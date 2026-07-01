#!/usr/bin/env bash
# Speedrun: replace the rsync'd anki with a proper git submodule checkout (so the
# anki web build can init its ftl translation submodules), then re-apply our
# topic_mastery change on top of the pinned anki 26.05b1.
set -euo pipefail
source "$HOME/.cargo/env"
cd "$HOME/aab"

echo "=== init anki submodule (pinned) ==="
rm -rf anki
git -c protocol.file.allow=always submodule update --init anki

echo "=== init ftl submodules ==="
( cd anki && git -c protocol.file.allow=always submodule update --init ftl/core-repo ftl/qt-repo )

echo "=== apply topic_mastery change from our fork ==="
SRC=/mnt/c/Users/frank/Documents/Alpha/Speedrun/anki
cp "$SRC/proto/anki/stats.proto"      anki/proto/anki/stats.proto
cp "$SRC/rslib/src/stats/mastery.rs"  anki/rslib/src/stats/mastery.rs
cp "$SRC/rslib/src/stats/mastery.sql" anki/rslib/src/stats/mastery.sql
cp "$SRC/rslib/src/stats/mod.rs"      anki/rslib/src/stats/mod.rs
cp "$SRC/rslib/src/stats/service.rs"  anki/rslib/src/stats/service.rs
grep -q "topic_mastery" anki/rslib/src/stats/service.rs && echo "topic_mastery change applied OK"

echo "=== FIX_DONE ==="
