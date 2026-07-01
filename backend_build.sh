#!/usr/bin/env bash
# Speedrun: cross-compile rsdroid (x86_64 Android) + host jar from our fork.
set -euo pipefail
source "$HOME/.cargo/env"
export ANDROID_HOME="$HOME/Android/Sdk"
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

cd "$HOME/aab"
echo "sdk.dir=$ANDROID_HOME" > local.properties

# The anki build derives a version hash from git; provide a minimal repo since
# the source was rsync'd without .git.
if [ ! -e anki/.git ]; then
  ( cd anki && git init -q && git -c user.email=build@local -c user.name=build commit --allow-empty -m build -q )
fi

echo "=== java/cargo versions ==="
java -version
cargo --version

echo "=== running build.sh (web + rust host + android x86_64 + gradle aar) ==="
bash ./build.sh

echo "=== BUILD_DONE ==="
echo "--- aar:"; ls -la rsdroid/build/outputs/aar/ 2>/dev/null || echo "no aar dir"
echo "--- testing jar:"; ls -la rsdroid-testing/build/libs/ 2>/dev/null || echo "no jar dir"
