# Linux development

Requirements: Linux x86_64, Python 3.11 or later, Git, curl, tar and unzip.
From the checkout:

```bash
bash scripts/bootstrap-linux.sh
bash scripts/validate-linux.sh
.venv/bin/python -m arena ui --open
```

The Bash bootstrap installs Oracle JDK 25.0.4.1 and Gradle 9.3.1 under
`.arena/tools`, verifies their SHA-256 hashes, installs the Python dependencies
and compiles the commits in `engine.lock.json`. Check Oracle licensing for use
outside development. Upstream source files are not modified.

If JDK 25 is already installed, `python scripts/bootstrap.py` also works on Linux.
For Windows, see the [PowerShell guide](windows.md).

`ARENA_TOOLS_DIR` and `GRADLE_USER_HOME` select tool and build caches. Use a
dedicated Gradle cache; the bootstrap writes its configuration there. The
machine HTTPS proxy is passed to Gradle with TLS verification enabled.
Where available, `/etc/ssl/certs/java/cacerts` supplies the Java trust store.
No provider keys are required for installation or offline validation.

Validation requires a built engine: `doctor` fails if it is missing, even when
unittest would otherwise skip integration tests. The validator checks replays,
18 control matches and resume without creating new attempts. Each invocation
uses a new directory unless an output path is supplied.

Fast checks without an engine:

```bash
python -m unittest discover -s tests -p test_arena.py -k ProtocolTests -v
```

Linux CI builds from a clean checkout and retains logs, reports and replays
on failure. Check the workflow result rather than assuming it passed.

After installation, matches use the Java path and local resources recorded in
`.arena/engine.json`; they do not contact a Leek Wars service or database.
Regenerate that file on each machine rather than copying it. Resume checks
runtime identity and does not merge runs across platforms or JVM profiles.
The runner fingerprint includes subpackages and prompts. Gradle archives use
stable file order and omit timestamps.

Native workers have heap, timeout and output limits. See the [full guide](complete-experiment.md)
for optional Docker isolation, MCP and API adapters. The [local interface](ui.md)
uses the same engine and requires no Node.js at runtime.
