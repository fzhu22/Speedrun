// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! The Speedrun AI lane (shared logic), ported from `pylib/anki/speedrun/ai.py`.
//!
//! AI never writes the card or the disconfirmer and never grades - it only offers
//! advice/hints, each degrading to a deterministic template when AI is off. The
//! actual HTTPS call runs on `Backend` (see `backend/speedrun_ai.rs`), which owns
//! the tokio runtime + web client; this module holds the prompts, the templates,
//! the config read, and the proxy call helper so both platforms share one lane.

use reqwest::Client;
use serde_json::json;
use serde_json::Value;

/// The hosted proxy that holds the real OpenAI key server-side (the client only
/// ever ships this URL + a revocable app token, so no key lives in the app).
/// Kept identical to the desktop `ai.py` constants.
const PROXY_URL: &str = "https://speedrun-ai-frank-pbr9.fly.dev/v1";
const APP_TOKEN: &str = "MYrFmMjbYCwAZ0vPnh9CxZkrfED7jZmdYful5uRMC6U";
const DEFAULT_MODEL: &str = "gpt-4.1-mini";

/// Collection-config key mirroring the desktop `speedrun_ai` config.
pub(crate) const AI_CONFIG_KEY: &str = "speedrun_ai";

/// Deterministic fallback for card advice when AI is off.
pub(crate) const CARD_ADVICE_TEMPLATE: &str =
    "Consider adding: the WHY behind the answer; a common wrong answer (the trap) this \
     catches; a boundary or edge case; and keep it to one idea with a specific, checkable \
     answer.";

/// Deterministic fallback for the disconfirmer hint when AI is off.
pub(crate) const HINT_TEMPLATE: &str =
    "Name the single fact the answer leans on. What assumption is it making, and what \
     change to that assumption would make the answer come out differently?";

/// Deterministic fallback for topic ideas on an empty card.
pub(crate) fn topic_ideas_fallback(topic: &str) -> String {
    let scope = if topic.is_empty() {
        String::new()
    } else {
        format!(" for {topic}")
    };
    format!(
        "Concepts worth a card{scope}: a key mechanism or definition; a cause -> effect \
         relationship; a common trap or exception; a quantitative relationship or formula."
    )
}

/// System prompts (kept identical to the desktop lane).
pub(crate) const CARD_ADVICE_SYSTEM: &str =
    "You are a study-card coach. Given a draft flashcard (and an optional topic), suggest \
     in at most 3 short bullet points what ELSE should go on the card to make it a strong, \
     exam-ready card - e.g. a missing 'why', a common trap, a boundary case, or a more \
     specific answer. Do NOT rewrite the card and do NOT give the answer; only advise.";
pub(crate) const TOPIC_IDEAS_SYSTEM: &str =
    "You are an MCAT study coach. Given a content topic, suggest 3-4 specific, high-yield \
     concepts a student could each turn into ONE flashcard. Reply as short bullet points \
     naming each concept (a mechanism, a relationship, a common trap, or an exception). Do \
     NOT write the questions or the answers.";
pub(crate) const HINT_SYSTEM: &str =
    "You are a Socratic study coach. Give ONE short hint (<= 2 sentences) that helps the \
     student find the single fact that would FLIP this answer. Do NOT state the \
     disconfirmer or reveal the answer - ask a probing question.";

/// The engine-side view of the `speedrun_ai` config (defaults mirror `_DEFAULTS`
/// in the desktop `ai.py`: on, gpt-4.1-mini).
pub(crate) struct AiConfig {
    pub enabled: bool,
    pub model: String,
}

pub(crate) fn read_ai_config(value: Option<Value>) -> AiConfig {
    let v = value.unwrap_or(Value::Null);
    let enabled = v.get("enabled").and_then(Value::as_bool).unwrap_or(true);
    let model = v
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or(DEFAULT_MODEL)
        .to_string();
    AiConfig { enabled, model }
}

/// One chat-completion call to the proxy. Returns the assistant text, or `None`
/// on any network/parse failure or empty output, so the caller falls back to the
/// deterministic template (the same degrade-to-template behavior as the Python).
pub(crate) async fn complete(client: &Client, model: &str, system: &str, user: &str) -> Option<String> {
    let body = json!({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    });
    let resp = client
        .post(format!("{PROXY_URL}/chat/completions"))
        .header("Authorization", format!("Bearer {APP_TOKEN}"))
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .ok()?;
    let data: Value = resp.json().await.ok()?;
    let content = data
        .get("choices")?
        .get(0)?
        .get("message")?
        .get("content")?
        .as_str()?
        .trim()
        .to_string();
    (!content.is_empty()).then_some(content)
}
