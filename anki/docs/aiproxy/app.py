"""Speedrun AI proxy: a tiny OpenAI-compatible reverse proxy.

The desktop app calls THIS endpoint with a revocable app token; the real OpenAI key
lives here as a server secret and never ships inside the client. Only
`/v1/chat/completions` is proxied, only allowlisted models are permitted, and requests
are rate-limited per IP so a leaked app token can be revoked and cannot run up an
unbounded bill.

Environment (secrets set via `fly secrets`, non-secrets in fly.toml):
  OPENAI_API_KEY        (required) the real upstream key - a Fly SECRET
  SPEEDRUN_PROXY_TOKEN  (required) the app token the client must present - a Fly SECRET
  OPENAI_BASE_URL       upstream base (default https://api.openai.com/v1)
  ALLOWED_MODELS        comma list (default "gpt-4.1-mini")
  RATE_LIMIT_PER_MIN    per-IP requests/min (default 30)
  UPSTREAM_TIMEOUT      seconds (default 30)
  PORT                  listen port (default 8080)
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

import requests
from flask import Flask, Response, jsonify, request

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
PROXY_TOKEN = os.environ.get("SPEEDRUN_PROXY_TOKEN", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
ALLOWED_MODELS = {
    m.strip()
    for m in os.environ.get("ALLOWED_MODELS", "gpt-4.1-mini").split(",")
    if m.strip()
}
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))
UPSTREAM_TIMEOUT = int(os.environ.get("UPSTREAM_TIMEOUT", "30"))

app = Flask(__name__)

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _rate_ok(ip: str) -> bool:
    """Simple per-IP sliding-window limiter (best-effort; single process)."""
    now = time.time()
    with _lock:
        dq = _hits[ip]
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_PER_MIN:
            return False
        dq.append(now)
        return True


def _client_ip() -> str:
    fwd = request.headers.get("Fly-Client-IP") or request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() or (request.remote_addr or "unknown")


@app.get("/health")
def health():
    ok = bool(OPENAI_API_KEY and PROXY_TOKEN)
    return ("ok" if ok else "misconfigured", 200 if ok else 503)


@app.post("/v1/chat/completions")
def chat_completions():
    auth = request.headers.get("Authorization", "")
    if not PROXY_TOKEN or auth != f"Bearer {PROXY_TOKEN}":
        return jsonify({"error": {"message": "unauthorized"}}), 401
    if not _rate_ok(_client_ip()):
        return jsonify({"error": {"message": "rate limited"}}), 429

    body = request.get_json(silent=True) or {}
    model = body.get("model")
    if model not in ALLOWED_MODELS:
        return jsonify({"error": {"message": f"model not allowed: {model}"}}), 400

    try:
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=UPSTREAM_TIMEOUT,
        )
    except requests.RequestException as exc:
        return jsonify({"error": {"message": f"upstream error: {exc}"}}), 502

    # Pass the upstream response through unchanged (status + JSON body).
    return Response(
        resp.content,
        status=resp.status_code,
        content_type=resp.headers.get("Content-Type", "application/json"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
