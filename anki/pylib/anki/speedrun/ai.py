"""The AI lane (brainlift SPOV 9 / PRD 6.4): classify card type and offer hints.

AI never writes the card or the disconfirmer and never grades - it only classifies and
gives severe-test hints, each carrying provenance. Everything degrades to a
deterministic path when AI is off, so the app runs with no AI configured.

Requests go through the Speedrun AI proxy (``docs/aiproxy/``), which holds the real
OpenAI key server-side; the client only ever ships the proxy URL + a revocable app
token, so no OpenAI key lives in the app or the synced collection. For local
development, setting ``SPEEDRUN_AI_KEY`` (a real key) overrides the proxy and talks to
OpenAI directly.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    Protocol = object  # type: ignore

from anki.speedrun.cardtype import CardType, heuristic_classify
from anki.speedrun.models import Provenance

AI_CONFIG_KEY = "speedrun_ai"
KEY_ENV_VAR = "SPEEDRUN_AI_KEY"  # dev override: a real key -> talk to OpenAI directly

# Baked, non-secret client config for the hosted AI proxy (see docs/aiproxy/README.md).
# The real OpenAI key lives ONLY on the proxy as a server secret; the client ships this
# proxy URL + a revocable app token. Fill these in after deploying the proxy. Left empty
# they leave AI off (deterministic fallback), so the app still runs with nothing set.
DEFAULT_PROXY_URL = "https://speedrun-ai-frank-pbr9.fly.dev/v1"  # deployed proxy (docs/aiproxy)
APP_TOKEN = "MYrFmMjbYCwAZ0vPnh9CxZkrfED7jZmdYful5uRMC6U"  # the SPEEDRUN_PROXY_TOKEN configured on the proxy (baked below)

_DEFAULTS = {
    # On by default; when nothing is configured the client resolves to None and every
    # AI op falls back to its deterministic path (heuristic classify / template hint),
    # so the app still runs AI-off per the spec.
    "enabled": True,
    "model": "gpt-4.1-mini",
}

#: Fixed few-shot examples for the classifier prompt - kept DISJOINT from the eval gold
#: set (verified by the leakage check in ai_eval).
FEWSHOT_EXAMPLES: List[Tuple[str, str, CardType]] = [
    ("How many chambers does the human heart have?", "4", CardType.DECLARATIVE),
    (
        "Why does raising temperature speed up most reactions?",
        "More molecules exceed the activation energy",
        CardType.APPLICATION,
    ),
]

_TEMPLATE_HINT = (
    "Name the single fact the answer leans on. What assumption is it making, and what "
    "change to that assumption would make the answer come out differently?"
)


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str:  # pragma: no cover - interface
        ...


class NullClient:
    """AI-off marker (callers use None; this exists for explicitness/tests)."""

    def complete(self, system: str, user: str) -> str:
        raise RuntimeError("AI is disabled")


class OpenAICompatibleClient:
    """Minimal chat-completions client for any OpenAI-compatible endpoint."""

    def __init__(self, *, base_url: str, model: str, api_key: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        import requests

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# -- config / availability ----------------------------------------------------


def get_config(col) -> dict:
    stored = col.get_config(AI_CONFIG_KEY, default=None) or {}
    return {**_DEFAULTS, **stored}


def set_config(col, *, enabled=None, model=None) -> None:
    cfg = get_config(col)
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    if model:
        cfg["model"] = model
    col.set_config(AI_CONFIG_KEY, cfg)


def api_key() -> Optional[str]:
    """The bearer token the client presents: a real key from the env (dev override),
    else the baked proxy app token. None when neither is set, which turns AI off."""
    env = os.environ.get(KEY_ENV_VAR, "").strip()
    if env:
        return env
    return APP_TOKEN or None


def base_url() -> str:
    """Where requests go: OpenAI directly when a real dev key is in the env, otherwise
    the hosted proxy (which injects the real key server-side)."""
    if os.environ.get(KEY_ENV_VAR, "").strip():
        return os.environ.get("SPEEDRUN_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if DEFAULT_PROXY_URL:
        return DEFAULT_PROXY_URL.rstrip("/")
    return "https://api.openai.com/v1"


def set_runtime_key(key: str) -> None:
    """Dev override: make a real key available for this session via the env var, which
    routes calls straight to OpenAI (bypassing the proxy)."""
    if key and key.strip():
        os.environ[KEY_ENV_VAR] = key.strip()


def ai_available(col) -> bool:
    return bool(get_config(col).get("enabled")) and api_key() is not None


def resolve_client(col) -> Optional[LLMClient]:
    """The configured client, or None when AI is off (callers must handle None)."""
    if not ai_available(col):
        return None
    cfg = get_config(col)
    return OpenAICompatibleClient(
        base_url=base_url(), model=cfg["model"], api_key=api_key()
    )


# -- operations (all fall back deterministically when client is None) ---------


def classify_card_type(client: Optional[LLMClient], question: str, answer: str = "") -> CardType:
    if client is None:
        return heuristic_classify(question, answer)
    try:
        system = (
            "You label a flashcard with exactly one word: 'declarative' (a fact to "
            "recall) or 'application' (needs reasoning or transfer). Reply with only "
            "that word."
        )
        shots = "\n".join(
            f"Q: {q}\nA: {a}\nLabel: {t.value}" for q, a, t in FEWSHOT_EXAMPLES
        )
        out = client.complete(system, f"{shots}\n\nQ: {question}\nA: {answer}\nLabel:")
        out = out.strip().lower()
        if "application" in out:
            return CardType.APPLICATION
        if "declarative" in out:
            return CardType.DECLARATIVE
    except Exception as exc:  # any failure -> heuristic
        print("speedrun ai: classify failed, using heuristic:", exc)
    return heuristic_classify(question, answer)


def disconfirmer_hint(
    client: Optional[LLMClient], question: str, answer: str = ""
) -> Tuple[str, Provenance]:
    """A severe-test hint to help write the disconfirmer. Never the disconfirmer itself."""
    if client is None:
        return _TEMPLATE_HINT, Provenance(source="template")
    try:
        system = (
            "You are a Socratic study coach. Give ONE short hint (<= 2 sentences) that "
            "helps the student find the single fact that would FLIP this answer. Do NOT "
            "state the disconfirmer or reveal the answer - ask a probing question."
        )
        out = client.complete(system, f"Q: {question}\nA: {answer}\nHint:").strip()
        if out:
            model = getattr(client, "model", "ai")
            return out, Provenance(
                source=f"AI:{model}", locator="card", note="hint only; not the disconfirmer"
            )
    except Exception as exc:
        print("speedrun ai: hint failed, using template:", exc)
    return _TEMPLATE_HINT, Provenance(source="template")
