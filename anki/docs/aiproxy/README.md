# Speedrun AI proxy

A tiny OpenAI-compatible reverse proxy so the **real OpenAI key never ships in the app**.
The desktop client calls this proxy with a **revocable app token**; the proxy holds the
real key as a server secret and forwards requests to OpenAI.

```mermaid
flowchart LR
  app["Desktop app (ai.py)"] -- "Bearer APP_TOKEN" --> proxy
  subgraph fly [Fly.io]
    proxy["AI proxy /v1/chat/completions"]
  end
  proxy -- "Bearer real OPENAI_API_KEY (Fly secret)" --> openai["api.openai.com"]
```

Why a proxy: a key baked into a client binary/wheel/APK can always be extracted. A proxy
keeps the real key off the device entirely; the client only holds an app token that is
**revocable, rate-limited, and restricted to an allowlisted model**, so a leak is
contained (rotate the token, redeploy) rather than a stolen OpenAI key.

## What it does

- `POST /v1/chat/completions` - requires `Authorization: Bearer <SPEEDRUN_PROXY_TOKEN>`,
  restricts `model` to `ALLOWED_MODELS`, rate-limits per IP, then forwards to OpenAI with
  the real key and returns the response unchanged. It is OpenAI-compatible, so the client
  only had to change its `base_url` + token.
- `GET /health` - `200 ok` once the key + token are configured.

## Deploy (your step - needs your Fly account + OpenAI key)

```powershell
cd anki\docs\aiproxy
# pick a globally-unique app name + region; edit fly.toml's `app`/`primary_region` to match
fly apps create speedrun-ai-<you>
# secrets (never in the repo): the real key, and an app token you generate
fly secrets set OPENAI_API_KEY="sk-..." SPEEDRUN_PROXY_TOKEN="<generate-a-long-random-token>"
fly deploy --ha=false
fly status
curl https://speedrun-ai-<you>.fly.dev/health   # -> ok
```

Generate a strong app token, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Wire it into the client

Set the client's baked constants in [../../pylib/anki/speedrun/ai.py](../../pylib/anki/speedrun/ai.py):

- `DEFAULT_PROXY_URL = "https://speedrun-ai-<you>.fly.dev/v1"`
- `APP_TOKEN = "<the SPEEDRUN_PROXY_TOKEN you set above>"`

The client then talks to the proxy automatically; no OpenAI key lives in the app or its
UI. (`SPEEDRUN_AI_KEY` in the environment still overrides for local development.)

## Rotate / revoke the app token

If the app token leaks, rotate it without touching the real key:

```powershell
fly secrets set SPEEDRUN_PROXY_TOKEN="<new-token>"
```

Then update `APP_TOKEN` in `ai.py` and ship a new build. The old token stops working
immediately.

## Cost

Same profile as the sync server: one `shared-cpu-1x` / 256 MB machine that auto-stops to
zero when idle, shared IPv4, no volume -> effectively ~$0 for personal use (you pay only
for the seconds it is awake serving a call, plus your OpenAI usage).
