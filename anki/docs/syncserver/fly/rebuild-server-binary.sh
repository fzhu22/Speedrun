#!/usr/bin/env bash
# Speedrun: (re)build the static musl anki-sync-server from THIS fork and stage it
# next to the Dockerfile for `fly deploy`. Run inside WSL Ubuntu:
#     bash rebuild-server-binary.sh
#
# You only need this when the fork's sync code changes; the committed
# ./anki-sync-server is already a working build.
set -euo pipefail
source "$HOME/.cargo/env"
export DEBIAN_FRONTEND=noninteractive

ANKI_DIR="$HOME/aab/anki"   # the fork checkout also used for the Android backend build
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "=== ensure musl toolchain ==="
apt-get install -y --no-install-recommends musl-tools musl-dev >/tmp/musl_apt.log 2>&1 || true
rustup target add x86_64-unknown-linux-musl

echo "=== build (musl, release) ==="
cd "$ANKI_DIR"
export CC_x86_64_unknown_linux_musl=musl-gcc
cargo build -p anki-sync-server --release --target x86_64-unknown-linux-musl

# The Cargo workspace root is the Anki-Android-Backend checkout, so target/ is one
# level above the fork; find the produced binary rather than hard-coding the path.
BIN="$(find "$HOME/aab" -type f -path '*x86_64-unknown-linux-musl/release/anki-sync-server' | head -n1)"
echo "built: $BIN"

echo "=== strip + stage next to Dockerfile ==="
cp "$BIN" "$HERE/anki-sync-server"
strip "$HERE/anki-sync-server"
chmod +x "$HERE/anki-sync-server"
ls -la "$HERE/anki-sync-server"
file "$HERE/anki-sync-server"
echo "STAGED -> $HERE/anki-sync-server"
