#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="${ARENA_TOOLS_DIR:-$REPO_ROOT/.arena/tools}"
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$REPO_ROOT/.arena/gradle}"
mkdir -p "$TOOLS" "$GRADLE_USER_HOME"
if [ ! -x "$TOOLS/jdk-25/bin/javac" ]; then
  curl -fsSL https://download.oracle.com/java/25/archive/jdk-25.0.4.1_linux-x64_bin.tar.gz -o "$TOOLS/jdk.tar.gz"
  printf '%s  %s\n' 'dd7e7f51d23bcffe85f1a439577ce1c0190a33417b34afdb338f9b3897bdeaec' "$TOOLS/jdk.tar.gz" | sha256sum -c -
  mkdir -p "$TOOLS/jdk-25"
  tar -xzf "$TOOLS/jdk.tar.gz" -C "$TOOLS/jdk-25" --strip-components=1
  rm "$TOOLS/jdk.tar.gz"
fi
if [ ! -x "$TOOLS/gradle-9.3.1/bin/gradle" ]; then
  curl -fsSL https://downloads.gradle.org/distributions/gradle-9.3.1-bin.zip -o "$TOOLS/gradle.zip"
  printf '%s  %s\n' 'b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06' "$TOOLS/gradle.zip" | sha256sum -c -
  unzip -q "$TOOLS/gradle.zip" -d "$TOOLS"
  rm "$TOOLS/gradle.zip"
fi
export JAVA_HOME="$TOOLS/jdk-25"
export PATH="$JAVA_HOME/bin:$TOOLS/gradle-9.3.1/bin:$PATH"
python - <<'PY'
import os
from pathlib import Path
from urllib.parse import urlsplit
lines = ['org.gradle.workers.max=4']
proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
if proxy:
    parsed = urlsplit(proxy)
    if parsed.username or parsed.password:
        raise SystemExit('Authenticated proxy needs a separately configured Gradle credential binding')
    for scheme in ('https', 'http'):
        lines.extend([f'systemProp.{scheme}.proxyHost={parsed.hostname}',
                      f'systemProp.{scheme}.proxyPort={parsed.port or 80}'])
trust = Path('/etc/ssl/certs/java/cacerts')
if trust.exists():
    lines.append(f'systemProp.javax.net.ssl.trustStore={trust}')
Path(os.environ['GRADLE_USER_HOME'], 'gradle.properties').write_text('\n'.join(lines) + '\n')
PY
cd "$REPO_ROOT"
python -m arena setup --gradle "$TOOLS/gradle-9.3.1/bin/gradle"
python -m arena doctor
