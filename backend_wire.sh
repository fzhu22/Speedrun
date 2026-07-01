#!/usr/bin/env bash
# Speedrun: place the locally-built rsdroid artifacts where AnkiDroid's
# local_backend dependency expects them (Anki-Android-Backend beside the app).
set -euo pipefail
DST=/mnt/c/Users/frank/Documents/Alpha/Speedrun/Anki-Android-Backend
mkdir -p "$DST/rsdroid/build/outputs/aar" "$DST/rsdroid-testing/build/libs"
cp "$HOME/aab/rsdroid/build/outputs/aar/rsdroid-release.aar" "$DST/rsdroid/build/outputs/aar/"
cp "$HOME/aab/rsdroid-testing/build/libs/rsdroid-testing.jar" "$DST/rsdroid-testing/build/libs/"
echo "--- copied artifacts:"
ls -la "$DST/rsdroid/build/outputs/aar/" "$DST/rsdroid-testing/build/libs/"
echo "WIRE_COPY_DONE"
