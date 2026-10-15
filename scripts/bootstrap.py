#!/usr/bin/env python3
"""Portable setup using an installed JDK 25; no shell or administrator required."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit
import venv
import zipfile

ROOT = Path(__file__).resolve().parent.parent
GRADLE_VERSION = "9.3.1"
GRADLE_SHA256 = "b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06"


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Python >= 3.11 is required")
    env = dict(os.environ)
    if env.get("JAVA_HOME"):
        env["PATH"] = str(Path(env["JAVA_HOME"]) / "bin") + os.pathsep + env.get("PATH", "")
    if not shutil.which("git", path=env.get("PATH")):
        raise SystemExit("Install Git and add it to PATH first")
    java = shutil.which("java", path=env.get("PATH"))
    if not java:
        raise SystemExit("Install JDK 25 first and set JAVA_HOME or add its bin directory to PATH")
    result = subprocess.run([java, "-XshowSettings:properties", "-version"], env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    props = {k.strip(): v.strip() for line in result.stderr.splitlines() if " = " in line
             for k, v in [line.split(" = ", 1)]}
    if props.get("java.specification.version") != "25":
        raise SystemExit("JDK 25 is required; correct JAVA_HOME or PATH")
    home = Path(props["java.home"])
    if not (home / "bin" / ("javac.exe" if os.name == "nt" else "javac")).is_file():
        raise SystemExit("Install the full JDK 25, not only a JRE")
    env["JAVA_HOME"] = str(home)
    env["PATH"] = str(home / "bin") + os.pathsep + env.get("PATH", "")
    tools = Path(env.get("ARENA_TOOLS_DIR", ROOT / ".arena/tools")).resolve()
    tools.mkdir(parents=True, exist_ok=True)
    gradle = tools / f"gradle-{GRADLE_VERSION}" / "bin" / ("gradle.bat" if os.name == "nt" else "gradle")
    if not gradle.is_file():
        archive = tools / "gradle.zip"
        try:
            print(f"Downloading Gradle {GRADLE_VERSION} (SHA-256 verified)", flush=True)
            urllib.request.urlretrieve(f"https://downloads.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip", archive)
            with archive.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != GRADLE_SHA256:
                    raise SystemExit("Gradle checksum mismatch; archive refused")
            with zipfile.ZipFile(archive) as contents:
                contents.extractall(tools)
            if os.name != "nt":
                gradle.chmod(0o755)
        finally:
            archive.unlink(missing_ok=True)
    # A dedicated cache avoids overwriting the user's Gradle configuration.
    cache = ROOT / ".arena/gradle-portable"
    cache.mkdir(parents=True, exist_ok=True)
    env["GRADLE_USER_HOME"] = str(cache)
    lines = ["org.gradle.workers.max=4"]
    proxy = env.get("HTTPS_PROXY") or env.get("https_proxy")
    if proxy:
        parsed = urlsplit(proxy)
        if parsed.username or parsed.password or not parsed.hostname:
            raise SystemExit("Authenticated proxy requires a separately configured Gradle credential binding")
        for scheme in ("https", "http"):
            lines.extend([f"systemProp.{scheme}.proxyHost={parsed.hostname}",
                          f"systemProp.{scheme}.proxyPort={parsed.port or 80}"])
    trust = Path("/etc/ssl/certs/java/cacerts")
    if trust.is_file():
        lines.append(f"systemProp.javax.net.ssl.trustStore={trust}")
    (cache / "gradle.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    env["PYTHONUTF8"] = "1"
    for args in (["-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements/mcp.lock.txt"],
                 ["-m", "pip", "install", "--disable-pip-version-check", "--no-deps", "-e", "."],
                 ["-m", "arena", "setup", "--gradle", str(gradle)],
                 ["-m", "arena", "doctor"]):
        subprocess.run([str(python), *args], cwd=ROOT, env=env, check=True)
    print("Ready. Use .venv\\Scripts\\python.exe -m arena on Windows, or .venv/bin/python -m arena on Linux.")


if __name__ == "__main__":
    main()
