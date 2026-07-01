// SPDX-License-Identifier: GPL-3.0-or-later

package com.ichi2.anki.pages

import android.content.Context
import android.content.Intent
import com.ichi2.anki.common.destinations.SpeedrunDestination

/** Builds the [Intent] that opens the Speedrun dashboard screen. */
fun SpeedrunDestination.toIntent(context: Context): Intent = SpeedrunPage.getIntent(context)
