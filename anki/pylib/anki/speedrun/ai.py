"""The AI lane (brainlift SPOV 9 / PRD 6.4): classify card type and offer hints.

AI never writes the card or the disconfirmer and never grades - it only classifies and
gives severe-test hints, each carrying provenance. Everything degrades to a
deterministic path when AI is off (no key / disabled), so the app runs keyless.

Provider is OpenAI-compatible. The API key is read from the environment
(``SPEEDRUN_AI_KEY``) and is never written to the synced collection.
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
KEY_ENV_VAR = "SPEEDRUN_AI_KEY"
_DEFAULTS = {
    # On by default; with no API key the client resolves to None and every AI op falls
    # back to its deterministic path (heuristic classify / template hint), so the app
    # still runs keyless and AI-off per the spec.
    "enabled": True,
    "model": "gpt-4.1-mini",
    "base_url": "https://api.openai.com/v1",
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


def set_config(col, *, enabled=None, model=None, base_url=None) -> None:
    cfg = get_config(col)
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    if model:
        cfg["model"] = model
    if base_url:
        cfg["base_url"] = base_url
    col.set_config(AI_CONFIG_KEY, cfg)


def api_key() -> Optional[str]:
    key = os.environ.get(KEY_ENV_VAR, "").strip()
    return key or None


def set_runtime_key(key: str) -> None:
    """Make a key available for this session via the env var.

    The key is never written to the synced collection; the GUI persists it in a local,
    profile-only file and calls this on startup.
    """
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
        base_url=cfg["base_url"], model=cfg["model"], api_key=api_key()
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
