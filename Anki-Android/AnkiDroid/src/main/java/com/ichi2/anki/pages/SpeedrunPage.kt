// SPDX-License-Identifier: GPL-3.0-or-later

package com.ichi2.anki.pages

import android.content.Context
import android.content.Intent
import com.ichi2.anki.SingleFragmentActivity

/**
 * Speedrun dashboard, rendered from the shared SvelteKit `speedrun` page.
 *
 * Mirrors [Statistics]/[CongratsPage]: a [PageFragment] whose [pagePath] points the embedded
 * WebView at the page served by [AnkiServer], which proxies backend calls registered in
 * [PostRequestHandler].
 */
class SpeedrunPage : PageFragment() {
    override val pagePath = "speedrun"

    companion object {
        fun getIntent(context: Context): Intent = SingleFragmentActivity.getIntent(context, fragmentClass = SpeedrunPage::class)
    }
}
