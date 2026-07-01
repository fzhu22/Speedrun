#!/usr/bin/env bash
# Speedrun: provision the Linux toolchain and stage the Anki-Android-Backend
# build so rsdroid can be cross-compiled from our fork (with topic_mastery).
set -euo pipefail

echo "=== STAGE 1: apt packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends \
  openjdk-21-jdk-headless build-essential pkg-config libssl-dev \
  python3 rsync ca-certificates curl unzip

echo "=== STAGE 2: rustup 1.92.0 + android target ==="
if [ ! -d "$HOME/.rustup" ]; then
  curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.92.0 --profile minimal
fi
# shellcheck disable=SC1091
source "$HOME/.cargo/env"
rustup target add x86_64-linux-android
rustc --version

echo "=== STAGE 3: copy our anki fork (with topic_mastery) into aab/anki ==="
SRC=/mnt/c/Users/frank/Documents/Alpha/Speedrun/anki
mkdir -p "$HOME/aab/anki"
rsync -a --delete \
  --exclude out --exclude target --exclude node_modules \
  --exclude .git --exclude .gradle \
  "$SRC/" "$HOME/aab/anki/"
test -f "$HOME/aab/anki/rslib/src/stats/mastery.rs" && echo "mastery.rs present in submodule"

echo "=== STAGE 4: android cmdline-tools ==="
export ANDROID_HOME="$HOME/Android/Sdk"
mkdir -p "$ANDROID_HOME/cmdline-tools"
if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
  cd /tmp
  curl -sSLo cmdtools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  rm -rf cmdline-tools
  unzip -q cmdtools.zip
  mv cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
fi
SDKM="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
yes | "$SDKM" --licenses >/dev/null 2>&1 || true

echo "=== STAGE 5: sdk packages + ndk 29 (large download) ==="
"$SDKM" "platform-tools" "platforms;android-36" "build-tools;36.0.0" "ndk;29.0.14206865" >/dev/null

echo "=== DONE_SETUP ==="
