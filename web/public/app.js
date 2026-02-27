// 3CX Recordings & Transcriptions — Frontend
// Vanilla JS, no dependencies

(function () {
  "use strict";

  // ── State ──────────────────────────────────────────────────────────

  let currentPage = 0;
  let pageSize = 25;
  let expandedRow = null;

  // ── Tab Switching ──────────────────────────────────────────────────

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
    });
  });

  // ── Health Panel ───────────────────────────────────────────────────

  async function checkHealth() {
    try {
      const resp = await fetch("/api/health");
      const services = await resp.json();
      services.forEach((svc) => {
        const dot = document.querySelector(`.health-dot[data-service="${svc.name}"]`);
        if (dot) {
          dot.className = "health-dot " + (svc.status === "healthy" ? "healthy" : "error");
        }
      });
    } catch {
      document.querySelectorAll(".health-dot").forEach((d) => (d.className = "health-dot error"));
    }
  }

  checkHealth();
  setInterval(checkHealth, 30000);

  // ── Recordings ─────────────────────────────────────────────────────

  const recordingsBody = document.getElementById("recordings-body");
  const recordingsLoading = document.getElementById("recordings-loading");
  const recordingsEmpty = document.getElementById("recordings-empty");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const pageInfo = document.getElementById("page-info");
  const pageSizeSelect = document.getElementById("page-size");

  async function loadRecordings() {
    recordingsLoading.hidden = false;
    recordingsEmpty.hidden = true;
    recordingsBody.innerHTML = "";
    expandedRow = null;

    try {
      const skip = currentPage * pageSize;
      const resp = await fetch(`/api/recordings?top=${pageSize}&skip=${skip}`);
      const data = await resp.json();
      const recordings = data.value || data || [];

      recordingsLoading.hidden = true;

      if (recordings.length === 0) {
        recordingsEmpty.hidden = false;
        nextBtn.disabled = true;
        return;
      }

      recordings.forEach((rec) => {
        const tr = document.createElement("tr");
        const duration = rec.StartTime && rec.EndTime
          ? (new Date(rec.EndTime) - new Date(rec.StartTime)) / 1000
          : rec.Duration;
        const caller = rec.FromDisplayName || rec.FromCallerNumber || rec.Caller || "";
        const called = rec.ToDisplayName || rec.ToCallerNumber || rec.Called || "";
        tr.innerHTML = `
          <td><button class="expand-btn">&#9654;</button></td>
          <td>${esc(rec.Id)}</td>
          <td>${formatDate(rec.StartTime || rec.CallTime)}</td>
          <td>${formatDuration(duration)}</td>
          <td>${esc(caller)}</td>
          <td>${esc(called)}</td>
          <td>${esc(rec.CallType || "")}</td>
        `;

        tr.addEventListener("click", () => toggleDetail(tr, rec));
        recordingsBody.appendChild(tr);
      });

      prevBtn.disabled = currentPage === 0;
      nextBtn.disabled = recordings.length < pageSize;
      pageInfo.textContent = `Page ${currentPage + 1}`;
    } catch (err) {
      recordingsLoading.hidden = true;
      recordingsBody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--red)">Error loading recordings: ${esc(err.message)}</td></tr>`;
    }
  }

  function toggleDetail(tr, rec) {
    const btn = tr.querySelector(".expand-btn");
    const existing = tr.nextElementSibling;

    if (existing && existing.classList.contains("detail-row")) {
      existing.remove();
      btn.classList.remove("open");
      expandedRow = null;
      return;
    }

    // Close any other open detail
    if (expandedRow) {
      const oldBtn = expandedRow.previousElementSibling?.querySelector(".expand-btn");
      if (oldBtn) oldBtn.classList.remove("open");
      expandedRow.remove();
      expandedRow = null;
    }

    btn.classList.add("open");

    const detailTr = document.createElement("tr");
    detailTr.classList.add("detail-row");
    detailTr.innerHTML = `
      <td colspan="7">
        <div class="detail-content">
          <audio controls preload="none" src="/api/recordings/${rec.Id}/audio"></audio>
          <div class="detail-actions">
            <a href="/api/recordings/${rec.Id}/audio" download="recording_${rec.Id}.wav">Download WAV</a>
          </div>
          ${rec.Transcription ? `<div class="transcription"><strong>Transcription:</strong>\n${esc(rec.Transcription)}</div>` : ""}
          ${rec.Summary ? `<div class="summary"><strong>Summary:</strong> ${esc(rec.Summary)}</div>` : ""}
        </div>
      </td>
    `;

    // Prevent row click from toggling when clicking inside detail
    detailTr.addEventListener("click", (e) => e.stopPropagation());

    tr.after(detailTr);
    expandedRow = detailTr;
  }

  prevBtn.addEventListener("click", () => {
    if (currentPage > 0) { currentPage--; loadRecordings(); }
  });

  nextBtn.addEventListener("click", () => {
    currentPage++;
    loadRecordings();
  });

  pageSizeSelect.addEventListener("change", () => {
    pageSize = parseInt(pageSizeSelect.value);
    currentPage = 0;
    loadRecordings();
  });

  loadRecordings();

  // ── STT ────────────────────────────────────────────────────────────

  const dropZone = document.getElementById("drop-zone");
  const sttFile = document.getElementById("stt-file");
  const sttFileInfo = document.getElementById("stt-file-info");
  const sttFilename = document.getElementById("stt-filename");
  const sttClear = document.getElementById("stt-clear");
  const sttLanguage = document.getElementById("stt-language");
  const sttTranscribe = document.getElementById("stt-transcribe");
  const sttLoading = document.getElementById("stt-loading");
  const sttResult = document.getElementById("stt-result");
  const sttText = document.getElementById("stt-text");
  const sttCopy = document.getElementById("stt-copy");

  let selectedFile = null;

  dropZone.addEventListener("click", () => sttFile.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) selectSTTFile(e.dataTransfer.files[0]);
  });

  sttFile.addEventListener("change", () => {
    if (sttFile.files.length > 0) selectSTTFile(sttFile.files[0]);
  });

  function selectSTTFile(file) {
    selectedFile = file;
    sttFilename.textContent = file.name;
    sttFileInfo.hidden = false;
    dropZone.hidden = true;
    sttTranscribe.disabled = false;
    sttResult.hidden = true;
  }

  sttClear.addEventListener("click", () => {
    selectedFile = null;
    sttFile.value = "";
    sttFileInfo.hidden = true;
    dropZone.hidden = false;
    sttTranscribe.disabled = true;
    sttResult.hidden = true;
  });

  sttTranscribe.addEventListener("click", async () => {
    if (!selectedFile) return;

    sttTranscribe.disabled = true;
    sttLoading.hidden = false;
    sttResult.hidden = true;

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("model", "whisper-1");
      formData.append("response_format", "json");
      const lang = sttLanguage.value;
      if (lang) formData.append("language", lang);

      const resp = await fetch("/api/stt", { method: "POST", body: formData });
      const data = await resp.json();

      sttText.value = data.text || JSON.stringify(data, null, 2);
      sttResult.hidden = false;
    } catch (err) {
      sttText.value = "Error: " + err.message;
      sttResult.hidden = false;
    } finally {
      sttTranscribe.disabled = false;
      sttLoading.hidden = true;
    }
  });

  sttCopy.addEventListener("click", () => {
    navigator.clipboard.writeText(sttText.value).then(() => {
      sttCopy.textContent = "Copied!";
      setTimeout(() => (sttCopy.textContent = "Copy to Clipboard"), 2000);
    });
  });

  // ── TTS ────────────────────────────────────────────────────────────

  const ttsText = document.getElementById("tts-text");
  const ttsGenerate = document.getElementById("tts-generate");
  const ttsLoading = document.getElementById("tts-loading");
  const ttsResult = document.getElementById("tts-result");
  const ttsAudio = document.getElementById("tts-audio");
  const ttsDownload = document.getElementById("tts-download");
  const ttsDescription = document.getElementById("tts-description");
  const parlerDescGroup = document.getElementById("parler-desc-group");

  // Show/hide parler description field
  document.querySelectorAll('input[name="tts-engine"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      parlerDescGroup.hidden = radio.value !== "parler" || !radio.checked;
    });
  });

  ttsGenerate.addEventListener("click", async () => {
    const text = ttsText.value.trim();
    if (!text) return;

    const engine = document.querySelector('input[name="tts-engine"]:checked').value;
    const body = { text, engine };
    if (engine === "parler" && ttsDescription.value.trim()) {
      body.description = ttsDescription.value.trim();
    }

    ttsGenerate.disabled = true;
    ttsLoading.hidden = false;
    ttsResult.hidden = true;

    try {
      const resp = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) throw new Error(`TTS failed: ${resp.status}`);

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      ttsAudio.src = url;
      ttsDownload.href = url;
      ttsResult.hidden = false;
    } catch (err) {
      alert("TTS Error: " + err.message);
    } finally {
      ttsGenerate.disabled = false;
      ttsLoading.hidden = true;
    }
  });

  // ── Helpers ────────────────────────────────────────────────────────

  function esc(val) {
    if (val == null) return "";
    const div = document.createElement("div");
    div.textContent = String(val);
    return div.innerHTML;
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return dateStr;
    }
  }

  function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return "";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }
})();
