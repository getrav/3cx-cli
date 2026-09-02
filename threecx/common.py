"""Shared configuration, authentication, URL, and response primitives.

Owns the primitives genuinely duplicated between the 3CX CLI tools
(``3cx-config`` and ``3cx-call``): JSON config-file I/O, FQDN
normalization, the OAuth2 client-credentials token POST, cached-token
predicates, Bearer header construction, API URL building, and common
response rendering.

Each script keeps thin module-level wrappers around these helpers so the
existing mocking seams stay intact: tests patch module-level
``get_token`` / ``save_config`` / ``CONFIG_FILE`` on each script and the
global ``requests`` / ``time`` modules, all of which continue to resolve
exactly as before.

Token cache semantics deliberately remain per-script (the wrappers own
them): ``3cx-config`` caps cached lifetimes at 45 seconds, while
``3cx-call`` trusts the response's ``expires_in``.
"""

import json
import os
import sys

import requests


def load_config_file(path):
    """Read a JSON config file, returning {} when it does not exist."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_config_file(path, config):
    """Write a JSON config file with owner-only (0600) permissions."""
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(path, 0o600)


def normalize_fqdn(fqdn):
    """Strip scheme and trailing slashes from a user-supplied PBX host."""
    return fqdn.replace("https://", "").replace("http://", "").strip("/")


def has_valid_cached_token(config, now, leeway=5):
    """True when a cached access token exists and outlives now + leeway."""
    return bool(config.get("access_token")) and config.get("token_expiry", 0) > now + leeway


def token_expiry(now, expires_in, max_lifetime=None):
    """Absolute expiry timestamp, optionally capping the token lifetime."""
    lifetime = expires_in if max_lifetime is None else min(expires_in, max_lifetime)
    return now + lifetime


def request_client_token(fqdn, client_id, client_secret):
    """POST OAuth2 client credentials to /connect/token; return the JSON body."""
    url = f"https://{fqdn}/connect/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()


def bearer_headers(token):
    """Authorization + JSON content-type headers for a bearer token."""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def build_api_url(fqdn, base_path, path=""):
    """https URL for a PBX API base path with an optional sub-path."""
    base = f"https://{fqdn}/{base_path}"
    if path:
        return f"{base}/{path}"
    return base


def exit_on_error(resp):
    """Print an HTTP error to stderr and exit(1) for status >= 400."""
    if resp.status_code >= 400:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def print_json_or_text(resp):
    """Pretty-print a response body as JSON, falling back to raw text."""
    try:
        print(json.dumps(resp.json(), indent=2))
    except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
        print(resp.text)
