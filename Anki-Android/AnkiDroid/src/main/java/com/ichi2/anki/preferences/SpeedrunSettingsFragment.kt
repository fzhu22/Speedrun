// SPDX-License-Identifier: GPL-3.0-or-later

package com.ichi2.anki.preferences

import androidx.preference.Preference
import androidx.preference.SwitchPreferenceCompat
import com.ichi2.anki.CollectionManager.withCol
import com.ichi2.anki.R
import com.ichi2.anki.launchCatchingTask
import com.ichi2.anki.snackbar.showSnackbar
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put

/**
 * Speedrun study-feature toggles (the mobile equivalent of the desktop "Study features" dialog)
 * plus the "Fit performance model" action. Every value lives in the synced collection config, so
 * flipping it here changes the shared Rust engine's behaviour and syncs to desktop. The plain-bool
 * flags (fading, grading split, authoring guide) are stored directly; the disconfirmer and AI
 * settings live inside object configs, so only their `enabled` field is toggled (other fields kept).
 */
class SpeedrunSettingsFragment : SettingsFragment() {
    override val preferenceResource: Int
        get() = R.xml.preferences_speedrun
    override val analyticsScreenNameConstant: String
        get() = "prefs.speedrun"

    override fun initSubscreen() {
        // Object-config toggles: enabled lives inside speedrun_review / speedrun_ai.
        bindObjectEnabled(R.string.speedrun_pref_disconfirmer_key, "speedrun_review", default = true)
        bindObjectEnabled(R.string.speedrun_pref_ai_key, "speedrun_ai", default = true)

        // Plain-bool toggles.
        bindBool(R.string.speedrun_pref_fading_key, "speedrun_fading_enabled", default = true)
        bindBool(R.string.speedrun_pref_grading_split_key, "speedrun_grading_split_enabled", default = true)
        bindBool(R.string.speedrun_pref_authoring_guide_key, "speedrun_authoring_guide_enabled", default = true)

        // Fit-performance action (shared engine): recompute + set the enabled flag.
        requirePreference<Preference>(R.string.speedrun_pref_fit_performance_key).setOnPreferenceClickListener {
            launchCatchingTask {
                val res = withCol { backend.speedrunFitPerformance() }
                val verdict = if (res.passed) "enabled" else "still abstaining"
                showSnackbar("Performance $verdict (n=${res.n}, delta=${"%.3f".format(res.delta)})")
            }
            true
        }
    }

    private fun bindBool(
        keyRes: Int,
        configKey: String,
        default: Boolean,
    ) {
        requirePreference<SwitchPreferenceCompat>(keyRes).apply {
            launchCatchingTask { isChecked = withCol { config.get<Boolean>(configKey) ?: default } }
            setOnPreferenceChangeListener { newValue ->
                launchCatchingTask { withCol { config.set(configKey, newValue == true) } }
                true
            }
        }
    }

    private fun bindObjectEnabled(
        keyRes: Int,
        configKey: String,
        default: Boolean,
    ) {
        requirePreference<SwitchPreferenceCompat>(keyRes).apply {
            launchCatchingTask {
                isChecked =
                    withCol {
                        config.get<JsonObject>(configKey)?.get("enabled")?.jsonPrimitive?.booleanOrNull ?: default
                    }
            }
            setOnPreferenceChangeListener { newValue ->
                val enabled = newValue == true
                launchCatchingTask {
                    withCol {
                        val existing = config.get<JsonObject>(configKey)
                        val updated =
                            buildJsonObject {
                                existing?.forEach { (k, v) -> put(k, v) }
                                put("enabled", enabled)
                            }
                        config.set(configKey, updated)
                    }
                }
                true
            }
        }
    }
}
