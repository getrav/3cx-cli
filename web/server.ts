/**
 * 3CX Recordings & Transcriptions Web Server
 *
 * Bun HTTP server providing:
 * - 3CX XAPI proxy (read-only: recordings list + download)
 * - LocalVoice proxy (STT via Whisper, TTS via Piper/Parler)
 * - Health checks for all services
 * - Static file serving for the frontend
 */

import { readFileSync, existsSync } from "fs";
import { join, extname } from "path";

// ── Configuration ──────────────────────────────────────────────────

interface ThreeCXConfig {
  fqdn: string;
  client_id: string;
  client_secret: string;
  access_token?: string;
  token_expiry?: number;
}

const CONFIG_PATH = join(process.env.HOME ?? "", ".3cx-config.json");
const PORT = 7001;
const PUBLIC_DIR = join(import.meta.dir, "public");

const LOCALVOICE = {
  stt: process.env.LOCALVOICE_STT_URL ?? "http://localhost:8080",
  piper: process.env.LOCALVOICE_PIPER_URL ?? "http://localhost:8000",
  parler: process.env.LOCALVOICE_PARLER_URL ?? "http://localhost:8001",
};

// ── Token Management ───────────────────────────────────────────────

let cachedToken: string | null = null;
let tokenExpiry = 0;

function loadConfig(): ThreeCXConfig {
  if (!existsSync(CONFIG_PATH)) {
    throw new Error(`Config not found: ${CONFIG_PATH}. Run 3cx-config first.`);
  }
  return JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
}

async function getToken(): Promise<string> {
  const now = Date.now() / 1000;

  // Return cached token if still valid (30s safety buffer)
  if (cachedToken && tokenExpiry > now + 30) {
    return cachedToken;
  }

  // Check if config file has a valid token
  const config = loadConfig();
  if (config.access_token && (config.token_expiry ?? 0) > now + 30) {
    cachedToken = config.access_token;
    tokenExpiry = config.token_expiry!;
    return cachedToken;
  }

  // Request new token via OAuth2 client credentials
  const resp = await fetch(`https://${config.fqdn}/connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: config.client_id,
      client_secret: config.client_secret,
      grant_type: "client_credentials",
    }),
  });

  if (!resp.ok) {
    throw new Error(`Token request failed: ${resp.status} ${await resp.text()}`);
  }

  const data = (await resp.json()) as { access_token: string; expires_in?: number };
  cachedToken = data.access_token;
  tokenExpiry = now + (data.expires_in ?? 3600);
  return cachedToken;
}

async function threecxHeaders(): Promise<Record<string, string>> {
  const token = await getToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

function threecxUrl(path: string): string {
  const config = loadConfig();
  return `https://${config.fqdn}/xapi/v1/${path}`;
}

// ── MIME Types ──────────────────────────────────────────────────────

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

// ── Route Handlers ─────────────────────────────────────────────────

async function handleRecordingsList(url: URL): Promise<Response> {
  const top = url.searchParams.get("top") ?? "25";
  const skip = url.searchParams.get("skip") ?? "0";
  const headers = await threecxHeaders();
  const params = new URLSearchParams({
    $top: top,
    $skip: skip,
    $orderby: "Id desc",
  });
  const resp = await fetch(`${threecxUrl("Recordings")}?${params}`, { headers });
  const body = await resp.json();
  return Response.json(body, { status: resp.status });
}

async function handleRecordingAudio(id: string): Promise<Response> {
  const headers = await threecxHeaders();
  const resp = await fetch(
    threecxUrl(`Recordings/Pbx.DownloadRecording(recId=${id})`),
    { headers },
  );
  if (!resp.ok) {
    return new Response(`Download failed: ${resp.status}`, { status: resp.status });
  }
  return new Response(resp.body, {
    headers: {
      "Content-Type": "audio/wav",
      "Content-Disposition": `inline; filename="recording_${id}.wav"`,
    },
  });
}

async function handleSTT(req: Request): Promise<Response> {
  const formData = await req.formData();
  const resp = await fetch(`${LOCALVOICE.stt}/v1/audio/transcriptions`, {
    method: "POST",
    body: formData,
  });
  const body = await resp.json();
  return Response.json(body, { status: resp.status });
}

async function handleTTS(req: Request): Promise<Response> {
  const body = (await req.json()) as { text: string; engine?: string; description?: string };
  const engine = body.engine ?? "piper";
  const baseUrl = engine === "parler" ? LOCALVOICE.parler : LOCALVOICE.piper;

  const ttsBody: Record<string, string> = { text: body.text };
  if (body.description) ttsBody.description = body.description;

  const resp = await fetch(`${baseUrl}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ttsBody),
  });

  if (!resp.ok) {
    const err = await resp.text();
    return new Response(err, { status: resp.status });
  }

  return new Response(resp.body, {
    headers: {
      "Content-Type": "audio/wav",
      "Content-Disposition": 'attachment; filename="speech.wav"',
    },
  });
}

async function handleHealth(): Promise<Response> {
  const services = [
    { name: "3cx", check: () => checkThreeCX() },
    { name: "whisper", check: () => checkService(LOCALVOICE.stt) },
    { name: "piper", check: () => checkService(LOCALVOICE.piper) },
    { name: "parler", check: () => checkService(LOCALVOICE.parler) },
  ];

  const results = await Promise.all(
    services.map(async (svc) => {
      try {
        const status = await svc.check();
        return { name: svc.name, status };
      } catch {
        return { name: svc.name, status: "error" };
      }
    }),
  );

  return Response.json(results);
}

async function checkThreeCX(): Promise<string> {
  const headers = await threecxHeaders();
  const resp = await fetch(threecxUrl("SystemStatus"), {
    headers,
    signal: AbortSignal.timeout(5000),
  });
  return resp.ok ? "healthy" : "error";
}

async function checkService(baseUrl: string): Promise<string> {
  const resp = await fetch(`${baseUrl}/health`, {
    signal: AbortSignal.timeout(5000),
  });
  if (!resp.ok) return "error";
  const data = (await resp.json()) as { status?: string };
  return data.status === "healthy" ? "healthy" : data.status ?? "unknown";
}

function serveStatic(pathname: string): Response {
  const filePath = pathname === "/" ? join(PUBLIC_DIR, "index.html") : join(PUBLIC_DIR, pathname);

  // Prevent path traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    return new Response("Forbidden", { status: 403 });
  }

  const file = Bun.file(filePath);
  const ext = extname(filePath);
  const contentType = MIME_TYPES[ext] ?? "application/octet-stream";

  return new Response(file, {
    headers: { "Content-Type": contentType },
  });
}

// ── Server ─────────────────────────────────────────────────────────

Bun.serve({
  port: PORT,
  async fetch(req) {
    const url = new URL(req.url);
    const path = url.pathname;

    try {
      // API Routes
      if (path === "/api/recordings" && req.method === "GET") {
        return await handleRecordingsList(url);
      }

      const audioMatch = path.match(/^\/api\/recordings\/(\d+)\/audio$/);
      if (audioMatch && req.method === "GET") {
        return await handleRecordingAudio(audioMatch[1]);
      }

      if (path === "/api/stt" && req.method === "POST") {
        return await handleSTT(req);
      }

      if (path === "/api/tts" && req.method === "POST") {
        return await handleTTS(req);
      }

      if (path === "/api/health" && req.method === "GET") {
        return await handleHealth();
      }

      // Static files
      return serveStatic(path);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[${req.method} ${path}] ${message}`);
      return Response.json({ error: message }, { status: 500 });
    }
  },
});

console.log(`3CX Web UI running at http://localhost:${PORT}`);
