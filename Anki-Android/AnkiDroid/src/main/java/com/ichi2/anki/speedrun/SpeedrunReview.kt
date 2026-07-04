// SPDX-License-Identifier: GPL-3.0-or-later

package com.ichi2.anki.speedrun

import android.text.TextUtils
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.core.text.HtmlCompat
import com.google.android.material.button.MaterialButton
import androidx.fragment.app.FragmentActivity
import anki.scheduler.CardAnswer.Rating
import com.ichi2.anki.CollectionManager.withCol
import com.ichi2.anki.R
import com.ichi2.anki.launchCatchingTask
import com.ichi2.anki.libanki.CardId
import com.ichi2.utils.input
import com.ichi2.utils.message
import com.ichi2.utils.negativeButton
import com.ichi2.utils.positiveButton
import com.ichi2.utils.show
import com.ichi2.utils.stripHtml
import com.ichi2.utils.title
import timber.log.Timber
import java.util.concurrent.ConcurrentHashMap

/**
 * The card that was just answered, emitted by the new reviewer's `ReviewerViewModel` so that
 * `ReviewerFragment` (which has an `Activity`) can run the shared [SpeedrunReview.onCardAnswered]
 * hook. The legacy `Reviewer` already has an `Activity`, so it calls the hook directly.
 */
data class SpeedrunAnsweredCard(
    val cardId: CardId,
    val rating: Rating,
)

/**
 * Review-time Speedrun hooks shared between the legacy [com.ichi2.anki.Reviewer] and the new
 * [com.ichi2.anki.ui.windows.reviewer.ReviewerFragment], giving both study screens parity.
 *
 * Every method here is defensive: a backend hiccup (e.g. an older engine, or a transient error)
 * must never break the review flow, so all backend calls are wrapped in try/catch and log-and-continue.
 */
object SpeedrunReview {
    /**
     * Per-card count of "Again" presses in this app session, mirroring the desktop's
     * `_again_streak`. The engine adds the card's persistent lapses to gauge how stuck the
     * learner is, so repeated Again on the *same* card (even a plain fact) eventually crosses the
     * struggle threshold and prompts. In-memory by design: "struggling in this session" is the
     * signal we care about; it resets on a clean recall (Good/Easy) or once we prompt.
     */
    private val againStreak = ConcurrentHashMap<CardId, Int>()

    /**
     * Runs the Speedrun logic for a freshly answered card:
     *  1. records the review so the backend can update "fading",
     *  2. asks the backend whether the learner should be prompted for a disconfirmer, and
     *  3. if so, shows a dialog to capture (and optionally validate) the disconfirmer.
     *
     * The backend's `shouldPrompt` decides when to prompt (typically only on AGAIN/HARD when the
     * learner is struggling), so callers may invoke this after every answer.
     *
     * @param activity host used to show the optional disconfirmer dialog
     * @param cardId the card that was just answered
     * @param rating the [Rating] chosen; `rating.number` is sent as the proto `uint32`
     * @param sessionMisses number of misses so far this session (feeds the prompt heuristic)
     */
    suspend fun onCardAnswered(
        activity: FragmentActivity,
        cardId: CardId,
        rating: Rating,
        sessionMisses: Int = 0,
    ) {
        // The proto Rating enum is 0-based (AGAIN=0, HARD=1, GOOD=2, EASY=3), but the shared
        // engine uses Anki's 1-based ease (AGAIN=1, HARD=2, GOOD=3, EASY=4) - the same values
        // the desktop passes. Convert so that pressing Again actually counts as a miss.
        val ease = rating.number + 1

        // Track the in-session "Again" streak exactly like the desktop: Again bumps it, a clean
        // recall (Good/Easy) clears it, and Hard leaves it unchanged (a soft miss). The engine
        // adds the card's persistent lapses, so total misses = card.lapses + sessionMisses.
        when {
            ease == 1 -> againStreak[cardId] = (againStreak[cardId] ?: 0) + 1
            ease >= 3 -> againStreak.remove(cardId)
        }
        val effectiveMisses = (againStreak[cardId] ?: 0) + sessionMisses

        // (a) update fading
        try {
            withCol { backend.speedrunRecordReview(cardId = cardId, rating = ease) }
        } catch (e: Exception) {
            Timber.w(e, "speedrun: recordReview failed")
        }

        // (b) ask the backend whether to prompt for a disconfirmer (and whether the learner is
        // clearly struggling, which tailors the prompt's wording).
        val decision =
            try {
                withCol {
                    backend.speedrunShouldPromptDisconfirmer(
                        cardId = cardId,
                        rating = ease,
                        sessionMisses = effectiveMisses,
                    )
                }
            } catch (e: Exception) {
                Timber.w(e, "speedrun: shouldPromptDisconfirmer failed")
                null
            }

        // (c) prompt if requested
        if (decision?.shouldPrompt == true) {
            againStreak.remove(cardId) // don't immediately re-prompt the same card
            promptForDisconfirmer(activity, cardId, decision.struggling)
        }
    }

    /**
     * Ensures the Speedrun note types exist in the collection. Idempotent and safe to call on every
     * reviewer open; the backend creates the note types only if they are missing.
     */
    suspend fun ensureNotetypes() {
        try {
            withCol { backend.speedrunEnsureNotetypes() }
        } catch (e: Exception) {
            Timber.w(e, "speedrun: ensureNotetypes failed")
        }
    }

    private suspend fun promptForDisconfirmer(
        activity: FragmentActivity,
        cardId: CardId,
        struggling: Boolean,
    ) {
        // Load the missed card so the learner can look at what they got wrong while writing the
        // disconfirmer (mirrors the desktop dialog). Fields 0/1 are Front/Back for study cards.
        val (question, answer) =
            try {
                withCol {
                    val note = getCard(cardId).note(this)
                    stripHtml(note.fields.getOrElse(0) { "" }).trim() to
                        stripHtml(note.fields.getOrElse(1) { "" }).trim()
                }
            } catch (e: Exception) {
                Timber.w(e, "speedrun: could not load card Q&A for disconfirmer prompt")
                "" to ""
            }

        try {
            val view =
                LayoutInflater.from(activity).inflate(R.layout.dialog_speedrun_disconfirmer, null)
            view.findViewById<TextView>(R.id.speedrun_disconfirmer_intro).setText(
                if (struggling) {
                    R.string.speedrun_disconfirmer_intro_struggling
                } else {
                    R.string.speedrun_disconfirmer_intro
                },
            )
            view.findViewById<TextView>(R.id.speedrun_disconfirmer_card).text =
                HtmlCompat.fromHtml(
                    "<b>Q:</b> ${TextUtils.htmlEncode(question)}<br><br><b>A:</b> ${TextUtils.htmlEncode(answer)}",
                    HtmlCompat.FROM_HTML_MODE_LEGACY,
                )

            // Optional AI hint: a Socratic nudge (never the answer). Marks the card as
            // "assisted" so the desktop's anti-crutch monitor can compare cohorts.
            var hintUsed = false
            val hintLabel = view.findViewById<TextView>(R.id.speedrun_disconfirmer_hint_text)
            view.findViewById<MaterialButton>(R.id.speedrun_disconfirmer_hint_button).setOnClickListener {
                activity.launchCatchingTask {
                    val hint =
                        try {
                            withCol { backend.speedrunDisconfirmerHint(question = question, answer = answer) }
                        } catch (e: Exception) {
                            Timber.w(e, "speedrun: disconfirmerHint failed")
                            null
                        }
                    if (hint != null && hint.text.isNotEmpty()) {
                        hintUsed = true
                        val label = if (hint.source.startsWith("AI")) "AI hint" else "Hint"
                        hintLabel.text = "$label: ${hint.text}"
                        hintLabel.visibility = View.VISIBLE
                    }
                }
            }

            AlertDialog
                .Builder(activity)
                .show {
                    title(R.string.speedrun_disconfirmer_title)
                    positiveButton(R.string.speedrun_disconfirmer_save) { }
                    negativeButton(R.string.dialog_cancel)
                    setView(view)
                }.input(
                    hint = activity.getString(R.string.speedrun_disconfirmer_hint),
                    displayKeyboard = true,
                    allowEmpty = false,
                ) { dialog, text ->
                    val disconfirmer = text.toString()
                    dialog.dismiss()
                    activity.launchCatchingTask {
                        saveDisconfirmer(activity, cardId, disconfirmer, hintUsed)
                    }
                }
        } catch (e: Exception) {
            Timber.w(e, "speedrun: unable to show disconfirmer prompt")
        }
    }

    /**
     * Validates the [disconfirmer] with the backend; if the backend reports a problem, the learner is
     * asked whether to save it anyway, otherwise it is saved directly.
     */
    private suspend fun saveDisconfirmer(
        activity: FragmentActivity,
        cardId: CardId,
        disconfirmer: String,
        assisted: Boolean = false,
    ) {
        val problem =
            try {
                // The generated backend unwraps single-field responses, so this returns
                // the problem String directly ("" = ok), not a response message.
                withCol { backend.speedrunValidateDisconfirmer(text = disconfirmer, answer = "") }
            } catch (e: Exception) {
                Timber.w(e, "speedrun: validateDisconfirmer failed")
                ""
            }

        if (problem.isNotEmpty()) {
            // let the learner decide whether to keep a disconfirmer the backend flagged as weak
            try {
                AlertDialog
                    .Builder(activity)
                    .show {
                        title(R.string.speedrun_disconfirmer_save_anyway)
                        message(text = problem)
                        positiveButton(R.string.dialog_ok) {
                            activity.launchCatchingTask { createDisconfirmer(cardId, disconfirmer, assisted) }
                        }
                        negativeButton(R.string.dialog_cancel)
                    }
            } catch (e: Exception) {
                Timber.w(e, "speedrun: unable to show 'save anyway' prompt")
            }
            return
        }

        createDisconfirmer(cardId, disconfirmer, assisted)
    }

    private suspend fun createDisconfirmer(
        cardId: CardId,
        disconfirmer: String,
        assisted: Boolean = false,
    ) {
        try {
            withCol {
                backend.speedrunCreateDisconfirmer(
                    cardId = cardId,
                    disconfirmer = disconfirmer,
                    principle = "",
                    assisted = assisted,
                )
            }
        } catch (e: Exception) {
            Timber.w(e, "speedrun: createDisconfirmer failed")
        }
    }
}
