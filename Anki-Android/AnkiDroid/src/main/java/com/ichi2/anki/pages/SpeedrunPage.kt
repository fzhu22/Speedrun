// SPDX-License-Identifier: GPL-3.0-or-later

package com.ichi2.anki.pages

import android.content.Context
import android.content.Intent
import anki.decks.Deck
import anki.decks.DeckKt.FilteredKt.searchTerm
import anki.decks.copy
import com.ichi2.anki.CollectionManager.withCol
import com.ichi2.anki.Reviewer
import com.ichi2.anki.SingleFragmentActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import timber.log.Timber

/**
 * Speedrun dashboard, rendered from the shared SvelteKit `speedrun` page.
 *
 * Mirrors [Statistics]/[CongratsPage]: a [PageFragment] whose [pagePath] points the embedded
 * WebView at the page served by [AnkiServer], which proxies backend calls registered in
 * [PostRequestHandler].
 */
class SpeedrunPage : PageFragment() {
    override val pagePath = "speedrun"

    /**
     * Serve two Speedrun-only routes the shared dashboard page calls, in addition to the
     * standard [speedrunDashboard][com.ichi2.anki.libanki.speedrun.speedrunDashboardRaw] RPC
     * (routed by the parent class):
     *  - `speedrunEvidence`: the Evidence tab's data (see [readEvidenceAsset]).
     *  - `speedrunStudyTopic`: the "Study now" / plan-item loop (see [studyTopic]).
     * Everything else falls through to the shared [PageFragment] routing.
     */
    override suspend fun handlePostRequest(
        uri: PostRequestUri,
        bytes: ByteArray,
    ): ByteArray =
        when (uri.backendMethodName) {
            "speedrunEvidence" -> readEvidenceAsset()
            "speedrunStudyTopic" -> studyTopic(bytes)
            else -> super.handlePostRequest(uri, bytes)
        }

    private fun readEvidenceAsset(): ByteArray =
        try {
            requireContext().assets.open(EVIDENCE_ASSET).use { it.readBytes() }
        } catch (e: Exception) {
            // No bundled evidence (e.g. a build without the asset): return an empty-but-valid
            // payload so the Evidence tab shows "no artifacts" rather than erroring.
            Timber.w(e, "speedrun: %s missing; serving empty evidence", EVIDENCE_ASSET)
            """{"available":false,"artifacts":[],"standing_nulls":[]}""".toByteArray()
        }

    /**
     * The core "study now" loop: build (reusing one deck, mirroring the desktop
     * implementation in `qt/aqt/speedrun/home.py`) a filtered deck of the topic's cards and
     * open the reviewer. Defensive - a failure here (e.g. no matching cards) must not crash
     * the dashboard; it just does nothing and the student stays on Speedrun.
     */
    private suspend fun studyTopic(bytes: ByteArray): ByteArray {
        val code = bytes.toString(Charsets.UTF_8).filter { it.isLetterOrDigit() }
        val act = activity
        if (code.isEmpty() || act == null) return EMPTY_OK
        try {
            withCol {
                val existingId = decks.byName(DECK_NAME)?.id ?: 0L
                val current = sched.getOrCreateFilteredDeck(existingId)
                val updated =
                    current.copy {
                        name = DECK_NAME
                        config =
                            config.copy {
                                reschedule = true
                                searchTerms.clear()
                                searchTerms.add(
                                    searchTerm {
                                        // Match the content-category code as a full tag
                                        // segment, plus its finer children.
                                        search = "\"tag:*::$code\" OR \"tag:*::$code::*\""
                                        limit = 200
                                        order = Deck.Filtered.SearchTerm.Order.RANDOM
                                    },
                                )
                            }
                    }
                val result = sched.addOrUpdateFilteredDeck(updated)
                decks.select(result.id)
            }
            withContext(Dispatchers.Main) {
                act.startActivity(Reviewer.getIntent(act))
            }
        } catch (e: Exception) {
            Timber.w(e, "speedrun: studyTopic failed for topic %s", code)
        }
        return EMPTY_OK
    }

    companion object {
        private const val EVIDENCE_ASSET = "speedrun-evidence.json"

        // Reused for every topic, like the desktop side, so we never accumulate one filtered
        // deck per topic studied.
        private const val DECK_NAME = "Speedrun study"
        private val EMPTY_OK = """{"ok":true}""".toByteArray()

        fun getIntent(context: Context): Intent = SingleFragmentActivity.getIntent(context, fragmentClass = SpeedrunPage::class)
    }
}
