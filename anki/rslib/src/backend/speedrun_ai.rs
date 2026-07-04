// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Backend impl of the Speedrun AI lane: the RPCs that make an outbound HTTPS
//! call to the proxy. They live on `Backend` (which owns the tokio runtime + web
//! client), and each degrades to the deterministic template when AI is off or the
//! call fails - matching the desktop Python lane.

use anki_proto::speedrun::SpeedrunAdviceRequest;
use anki_proto::speedrun::SpeedrunAiResponse;
use anki_proto::speedrun::SpeedrunHintRequest;
use anki_proto::speedrun::SpeedrunTopicIdeasRequest;
use serde_json::Value;

use super::Backend;
use crate::prelude::*;
use crate::speedrun::ai;

impl crate::services::BackendSpeedrunService for Backend {
    fn speedrun_card_advice(&self, input: SpeedrunAdviceRequest) -> Result<SpeedrunAiResponse> {
        let cfg = self.speedrun_ai_config()?;
        if !cfg.enabled {
            return Ok(template(ai::CARD_ADVICE_TEMPLATE.to_string()));
        }
        let user = format!(
            "Topic: {}\nFront: {}\nBack: {}\nAdvice:",
            input.topic, input.question, input.answer
        );
        Ok(self.speedrun_ai_call(&cfg.model, ai::CARD_ADVICE_SYSTEM, &user, ai::CARD_ADVICE_TEMPLATE))
    }

    fn speedrun_topic_ideas(&self, input: SpeedrunTopicIdeasRequest) -> Result<SpeedrunAiResponse> {
        let cfg = self.speedrun_ai_config()?;
        let fallback = ai::topic_ideas_fallback(&input.topic);
        if !cfg.enabled {
            return Ok(template(fallback));
        }
        let user = format!("Topic: {}\nConcepts to make cards about:", input.topic);
        Ok(self.speedrun_ai_call(&cfg.model, ai::TOPIC_IDEAS_SYSTEM, &user, &fallback))
    }

    fn speedrun_disconfirmer_hint(&self, input: SpeedrunHintRequest) -> Result<SpeedrunAiResponse> {
        let cfg = self.speedrun_ai_config()?;
        if !cfg.enabled {
            return Ok(template(ai::HINT_TEMPLATE.to_string()));
        }
        let user = format!("Q: {}\nA: {}\nHint:", input.question, input.answer);
        Ok(self.speedrun_ai_call(&cfg.model, ai::HINT_SYSTEM, &user, ai::HINT_TEMPLATE))
    }
}

fn template(text: String) -> SpeedrunAiResponse {
    SpeedrunAiResponse {
        text,
        source: "template".to_string(),
    }
}

impl Backend {
    fn speedrun_ai_config(&self) -> Result<ai::AiConfig> {
        let value = self.with_col(|col| Ok(col.get_config_optional::<Value, _>(ai::AI_CONFIG_KEY)))?;
        Ok(ai::read_ai_config(value))
    }

    /// Run one proxy call on the backend runtime, returning the AI text with an
    /// `AI:<model>` source, or the deterministic `fallback` with a `template`
    /// source on any failure.
    fn speedrun_ai_call(
        &self,
        model: &str,
        system: &str,
        user: &str,
        fallback: &str,
    ) -> SpeedrunAiResponse {
        let client = self.web_client();
        let out = self
            .runtime_handle()
            .block_on(ai::complete(&client, model, system, user));
        match out {
            Some(text) => SpeedrunAiResponse {
                text,
                source: format!("AI:{model}"),
            },
            None => template(fallback.to_string()),
        }
    }
}
