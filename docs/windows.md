# Native Windows setup (PowerShell)

The runner, experiments, MCP and exports work with Windows Python and Java.
WSL and Bash are not required. The **Windows native engine** CI workflow builds
the engine and runs the integration suite. Check its result for your commit.

## Prerequisites

- [Python 3.11 or later](https://www.python.org/downloads/windows/) with the `py`
  launcher. CI uses Python 3.12.
- [Git for Windows](https://git-scm.com/downloads/win), available in PowerShell.
- A full **JDK 25**, such as [Eclipse Temurin](https://adoptium.net/temurin/releases/?version=25).
  Set `JAVA_HOME` to its installation folder or add its `bin` directory to
  `PATH`, then open a new terminal.

The bootstrap downloads Gradle 9.3.1, verifies its SHA-256, creates `.venv`,
installs MCP dependencies and builds the pinned engine. Installation needs Internet access.

## Install

```powershell
git clone https://github.com/lesquoyb/llm_arena.git
cd llm_arena
py -3 scripts/bootstrap.py
```

For an existing checkout, update the branch you use and run the last command.
Gradle is stored in `.arena/tools` and uses `.arena/gradle-portable` as its
cache. `ARENA_TOOLS_DIR` can change the tools location.

If Java is not found, set the actual JDK path for this terminal:

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\YOUR_JDK_25_FOLDER'
py -3 scripts/bootstrap.py
```

`JAVA_HOME` takes priority over `PATH`. Use a JDK, not just a JRE.
A `getaddrinfo failed` error during download means a DNS lookup failed.
Check the connection, VPN and proxy. Gradle downloads can redirect through
GitHub and `release-assets.githubusercontent.com`.

## Start the interface

```powershell
.\.venv\Scripts\python.exe -m arena ui --open
```

The browser opens http://127.0.0.1:8765. Keep the terminal open.
Ctrl+C stops the server and requests a checkpointed stop of its active run.
See the [interface guide](ui.md).

Using the venv executable directly avoids changing PowerShell execution policy.

## Run from the command line

```powershell
.\.venv\Scripts\python.exe -m arena doctor
.\.venv\Scripts\python.exe -m arena fight examples/strategies/rush examples/strategies/passive
.\.venv\Scripts\python.exe -m arena experiment plan configs/offline-complete.json
.\.venv\Scripts\python.exe -m arena experiment run configs/offline-complete.json --out runs/my-first-test
.\.venv\Scripts\python.exe -m arena experiment resume runs/my-first-test
.\.venv\Scripts\python.exe -m arena experiment status runs/my-first-test
.\.venv\Scripts\python.exe -m arena experiment export runs/my-first-test --out runs/my-export
```

The demo uses mock participants with predefined code and real Java matches.
It makes no API calls. It plans 80 evaluation matches plus preparation tests.
Read `analysis.md` for scores and `report.md` for execution status.

Use a new directory for a new run or export. Resume requires the original code,
configuration and runtime. A Linux run cannot silently resume on Windows;
exported results remain readable on both platforms.

## Validation and limits

```powershell
.\.venv\Scripts\python.exe scripts/validate.py
```

Validation runs the engine check, tests, an 18-match tournament and a resume
that must reuse all match artifacts. It can take several minutes.
See [MCP and Docker](complete-experiment.md#mcp) and [provider settings](providers.md).
The Docker image build script is a Linux tool and is not needed for native Windows.

Native workers have a Java heap limit, a whole-process timeout and output quotas.
Windows polls an 8 MB per-file output limit, so a file can briefly exceed it.
Linux also uses an OS file-size limit. Windows cleanup uses `taskkill /T /F`
to stop child processes. OS locks are released when their owning process exits.

After an update that changes the Java adapter, rerun the bootstrap and restart
the UI. Existing results remain readable; resuming them still requires their original runtime.
