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
#: Per-model cache of the held-out cutoff eval, so the AI classifier is only trusted
#: after it clears the gate once (synced via collection config).
AI_GATE_KEY = "speedrun_ai_gate"
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

#: Deterministic fallback for card_advice when AI is off (a fixed authoring checklist).
_CARD_ADVICE_TEMPLATE = (
    "Consider adding: the WHY behind the answer; a common wrong answer (the trap) this "
    "catches; a boundary or edge case; and keep it to one idea with a specific, "
    "checkable answer."
)


def _topic_ideas_fallback(topic: str = "") -> str:
    where = f" for {topic}" if topic else ""
    return (
        f"Concepts worth a card{where}: a key mechanism or definition; a cause -> effect "
        "relationship; a common trap or exception; a quantitative relationship or formula."
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


# -- classifier cutoff gate ---------------------------------------------------
# "Evaluate before students see it": the AI classifier is only trusted after it clears
# a pre-registered accuracy cutoff AND beats the heuristic baseline on the held-out gold
# set. The verdict is cached per model in synced config; until it passes, classification
# falls back to the deterministic heuristic.


def classifier_gate(col) -> dict:
    """Per-model cache of the held-out cutoff eval (synced collection config)."""
    return col.get_config(AI_GATE_KEY, default=None) or {}


def cache_classifier_gate(col, model: str, result: dict) -> None:
    """Persist a gate result (main thread only - it writes the collection)."""
    gate = classifier_gate(col)
    gate[model] = result
    col.set_config(AI_GATE_KEY, gate)


def classifier_passes_gate(col) -> bool:
    """Whether the AI classifier has already cleared the cutoff for the current model.
    Cache-read only (safe on the main thread, no network). Unknown/off -> False."""
    if not ai_available(col):
        return False
    entry = classifier_gate(col).get(get_config(col)["model"])
    return bool(entry and entry.get("passed"))


def run_classifier_gate_eval(client: Optional[LLMClient]) -> dict:
    """Run the held-out card-type eval on ``client`` vs the heuristic baseline and return
    ``{passed, accuracy, baseline}``. Network-only and collection-free, so it is safe to
    call off the main thread. ``passed`` requires clearing the cutoff AND beating the
    baseline; any failure/exception resolves to not-passed (use the heuristic)."""
    from anki.speedrun import ai_eval

    if client is None:
        return {"passed": False, "accuracy": 0.0, "baseline": 0.0}
    try:
        scores = ai_eval.compare(
            lambda q, a: classify_card_type(client, q, a), heuristic_classify
        )
        passed = ai_eval.passes_cutoff(scores["ai"]) and scores["ai"] >= scores["heuristic"]
        return {"passed": passed, "accuracy": scores["ai"], "baseline": scores["heuristic"]}
    except Exception as exc:  # never let the gate break studying
        print("speedrun ai: classifier gate eval failed, using heuristic:", exc)
        return {"passed": False, "accuracy": 0.0, "baseline": 0.0}


def classify_items(
    client: Optional[LLMClient],
    items: List[Tuple[int, str, str]],
    gate_cached: Optional[dict],
) -> Tuple[Optional[dict], List[Tuple[int, "CardType", Provenance]]]:
    """Off-thread classify: decide whether to trust the AI classifier (running the
    held-out gate eval once when ``gate_cached`` is None), then label each
    ``(nid, question, answer)``. Returns ``(new_gate_result_or_None, [(nid, type,
    provenance)])``. Collection-free so it can run in a background task; the caller
    writes the gate result + tags back on the main thread."""
    gate_result: Optional[dict] = None
    use_ai = False
    if client is not None:
        if gate_cached is not None:
            use_ai = bool(gate_cached.get("passed"))
        else:
            gate_result = run_classifier_gate_eval(client)
            use_ai = bool(gate_result.get("passed"))
    classifier = client if use_ai else None
    labelled = [
        (nid, *classify_card_type_with_source(classifier, q, a)) for nid, q, a in items
    ]
    return gate_result, labelled


# -- operations (all fall back deterministically when client is None) ---------


def classify_card_type_with_source(
    client: Optional[LLMClient], question: str, answer: str = ""
) -> Tuple[CardType, Provenance]:
    """Classify a card AND name the source of the label, so every AI output is
    traceable. Source is ``AI:<model>`` when the model produced the label, or
    ``heuristic`` when AI is off or the call fell back."""
    if client is None:
        return heuristic_classify(question, answer), Provenance(source="heuristic")
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
        model = getattr(client, "model", "ai")
        prov = Provenance(source=f"AI:{model}", locator="card", note="card-type label")
        if "application" in out:
            return CardType.APPLICATION, prov
        if "declarative" in out:
            return CardType.DECLARATIVE, prov
    except Exception as exc:  # any failure -> heuristic
        print("speedrun ai: classify failed, using heuristic:", exc)
    return heuristic_classify(question, answer), Provenance(source="heuristic")


def classify_card_type(client: Optional[LLMClient], question: str, answer: str = "") -> CardType:
    """Just the label (used by the eval/baseline comparison)."""
    return classify_card_type_with_source(client, question, answer)[0]


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


def card_advice(
    client: Optional[LLMClient], question: str, answer: str = "", topic: str = ""
) -> Tuple[str, Provenance]:
    """Advice on what ELSE should go on a draft card while authoring it.

    Never rewrites the card and never gives the answer - it only suggests additions
    (a missing "why", a common trap, a boundary case, a cleaner answer). Uses AI when
    available, else a deterministic checklist; every result carries provenance.
    """
    if client is None:
        return _CARD_ADVICE_TEMPLATE, Provenance(source="template")
    try:
        system = (
            "You are a study-card coach. Given a draft flashcard (and an optional topic), "
            "suggest in at most 3 short bullet points what ELSE should go on the card to "
            "make it a strong, exam-ready card - e.g. a missing 'why', a common trap, a "
            "boundary case, or a more specific answer. Do NOT rewrite the card and do NOT "
            "give the answer; only advise."
        )
        user = f"Topic: {topic}\nFront: {question}\nBack: {answer}\nAdvice:"
        out = client.complete(system, user).strip()
        if out:
            model = getattr(client, "model", "ai")
            return out, Provenance(
                source=f"AI:{model}", locator="card", note="authoring advice; not the card"
            )
    except Exception as exc:
        print("speedrun ai: card advice failed, using template:", exc)
    return _CARD_ADVICE_TEMPLATE, Provenance(source="template")


def topic_card_ideas(
    client: Optional[LLMClient], topic: str = ""
) -> Tuple[str, Provenance]:
    """Concept suggestions for a *blank* draft: what could each become a card about.

    Used when the user asks for a hint on an empty card - it names high-yield concepts
    for the chosen topic (never writes the questions/answers). AI when available, else a
    deterministic checklist; carries provenance.
    """
    if client is None:
        return _topic_ideas_fallback(topic), Provenance(source="template")
    try:
        system = (
            "You are an MCAT study coach. Given a content topic, suggest 3-4 specific, "
            "high-yield concepts a student could each turn into ONE flashcard. Reply as "
            "short bullet points naming each concept (a mechanism, a relationship, a "
            "common trap, or an exception). Do NOT write the questions or the answers."
        )
        user = f"Topic: {topic}\nConcepts to make cards about:"
        out = client.complete(system, user).strip()
        if out:
            model = getattr(client, "model", "ai")
            return out, Provenance(
                source=f"AI:{model}", locator="topic", note="card ideas; not the card"
            )
    except Exception as exc:
        print("speedrun ai: card ideas failed, using template:", exc)
    return _topic_ideas_fallback(topic), Provenance(source="template")
