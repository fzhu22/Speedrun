#!/usr/bin/env bash
# Speedrun: sync the new SpeedrunService engine + shared page from the Windows anki
# fork into the WSL Anki-Android-Backend checkout (~/aab/anki), so the rsdroid AAR is
# rebuilt with them. Only additive/new files + the 3 additive wiring files are copied.
set -euo pipefail
SRC=/mnt/c/Users/frank/Documents/Alpha/Speedrun/anki
DST="$HOME/aab/anki"

echo "=== copy new proto + rust module + shared page ==="
cp "$SRC/proto/anki/speedrun.proto" "$DST/proto/anki/speedrun.proto"
rm -rf "$DST/rslib/src/speedrun"
cp -r "$SRC/rslib/src/speedrun" "$DST/rslib/src/speedrun"
rm -rf "$DST/ts/routes/speedrun"
cp -r "$SRC/ts/routes/speedrun" "$DST/ts/routes/speedrun"

echo "=== copy the 3 additive wiring files (base + speedrun edits only) ==="
cp "$SRC/rslib/src/lib.rs" "$DST/rslib/src/lib.rs"
cp "$SRC/rslib/proto/src/lib.rs" "$DST/rslib/proto/src/lib.rs"
cp "$SRC/rslib/proto/python.rs" "$DST/rslib/proto/python.rs"

echo "=== force reconfigure (stale build.ninja predates speedrun.proto) ==="
rm -f "$DST/out/build.ninja"

echo "=== verify ==="
ls -1 "$DST/rslib/src/speedrun"
ls -1 "$DST/ts/routes/speedrun"
grep -n "mod speedrun" "$DST/rslib/src/lib.rs" || echo "WARN: 'mod speedrun' missing"
grep -n "speedrun" "$DST/rslib/proto/src/lib.rs" || echo "WARN: proto speedrun registration missing"
grep -c "Speedrun" "$DST/proto/anki/speedrun.proto" || true
echo "SYNC_DONE"
