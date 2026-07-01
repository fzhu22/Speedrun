// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

use crate::collection::Collection;
use crate::error;

impl crate::services::SpeedrunService for Collection {
    fn speedrun_dashboard(
        &mut self,
        input: anki_proto::speedrun::SpeedrunDashboardRequest,
    ) -> error::Result<anki_proto::speedrun::SpeedrunDashboardResponse> {
        self.speedrun_dashboard(input)
    }

    fn speedrun_record_review(
        &mut self,
        input: anki_proto::speedrun::SpeedrunRecordReviewRequest,
    ) -> error::Result<anki_proto::speedrun::SpeedrunRecordReviewResponse> {
        self.speedrun_record_review(input)
    }

    fn speedrun_should_prompt_disconfirmer(
        &mut self,
        input: anki_proto::speedrun::SpeedrunShouldPromptRequest,
    ) -> error::Result<anki_proto::speedrun::SpeedrunShouldPromptResponse> {
        self.speedrun_should_prompt_disconfirmer(input)
    }

    fn speedrun_validate_disconfirmer(
        &mut self,
        input: anki_proto::speedrun::SpeedrunValidateDisconfirmerRequest,
    ) -> error::Result<anki_proto::speedrun::SpeedrunValidateDisconfirmerResponse> {
        self.speedrun_validate_disconfirmer(input)
    }

    fn speedrun_create_disconfirmer(
        &mut self,
        input: anki_proto::speedrun::SpeedrunCreateDisconfirmerRequest,
    ) -> error::Result<anki_proto::speedrun::SpeedrunCreateDisconfirmerResponse> {
        self.speedrun_create_disconfirmer(input)
    }

    fn speedrun_ensure_notetypes(&mut self) -> error::Result<()> {
        self.speedrun_ensure_notetypes()
    }
}
