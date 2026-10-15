from __future__ import annotations

import os
import platform
import signal
import shutil
import subprocess
import time
import re
from uuid import uuid4
from pathlib import Path

from .core import ArenaError, ROOT, STATE_ROOT, copy_submission, digest, file_hash, make_scenario, read_json, scratch_directory, submission, tree_hash, write_json


def command(args, cwd=ROOT, **kwargs):
    try:
        return subprocess.run([str(a) for a in args], cwd=cwd, check=True, **kwargs)
    except (OSError, subprocess.CalledProcessError) as e:
        raise ArenaError(f"Command failed: {args[0]}: {e}") from e


def capture(args, cwd=ROOT):
    return command(args, cwd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def java_home() -> Path:
    binary = shutil.which("java")
    if not binary:
        raise ArenaError("Java JDK 25 is required")
    result = command([binary, "-XshowSettings:properties", "-version"], capture_output=True, text=True)
    props = {key.strip(): value.strip() for line in result.stderr.splitlines() if " = " in line
             for key, value in [line.split(" = ", 1)]}
    if props.get("java.specification.version") != "25":
        raise ArenaError("Put Java JDK 25 on PATH before setup")
    home = Path(props["java.home"])
    if not (home / "bin" / ("javac.exe" if os.name == "nt" else "javac")).exists():
        raise ArenaError("A full JDK with javac is required")
    return home


def worker_limits():
    # Bound each redirected output file. This is not a complete OS sandbox.
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (8_000_000, 8_000_000))


def setup(gradle: str | None = None):
    lock = read_json(ROOT / "engine.lock.json")
    vendor = ROOT / "vendor" / "leek-wars-generator"
    if not vendor.exists():
        command(["git", "clone", lock["repository"], vendor])
        command(["git", "checkout", "--detach", lock["commit"]], vendor)
    if capture(["git", "rev-parse", "HEAD"], vendor) != lock["commit"]:
        raise ArenaError("Engine checkout does not match engine.lock.json; use a fresh vendor checkout")
    command(["git", "-c", "url.https://github.com/.insteadOf=git@github.com:", "submodule", "update", "--init", "--recursive"], vendor)
    if capture(["git", "rev-parse", "HEAD"], vendor / "leekscript") != lock["leekscript_commit"]:
        raise ArenaError("LeekScript commit mismatch")
    for repo in (vendor, vendor / "leekscript"):
        if capture(["git", "status", "--porcelain", "--untracked-files=no"], repo):
            raise ArenaError(f"Engine sources have local modifications: {repo}")
    home = java_home()
    gradle = gradle or shutil.which("gradle")
    if not gradle:
        cache = Path(os.environ.get("GRADLE_USER_HOME", Path.home() / ".gradle")) / "wrapper" / "dists"
        candidates = sorted(cache.glob(f"gradle-{lock['gradle_version']}-bin/*/gradle-{lock['gradle_version']}/bin/gradle" + (".bat" if os.name == "nt" else "")))
        if candidates:
            gradle = str(candidates[0])
    if not gradle:
        raise ArenaError(f"Install Gradle {lock['gradle_version']} or pass --gradle PATH (upstream wrapper is too old)")
    version = capture([gradle, "--version"])
    if f"Gradle {lock['gradle_version']}" not in version:
        raise ArenaError(f"Gradle {lock['gradle_version']} is required for the pinned build")
    command([gradle, f"-Dorg.gradle.java.home={home}", "--no-daemon", "--init-script", ROOT / "engine/leekscript.init.gradle", "jar"], vendor)
    state = STATE_ROOT
    classes = state / "bridge"
    classes.mkdir(parents=True, exist_ok=True)
    jar = vendor / "generator.jar"
    command([home / "bin" / "javac", "-encoding", "UTF-8", "-cp", jar, "-d", classes, ROOT / "engine/ArenaMain.java"])
    metadata = {
        "lock": lock, "java": str(home / "bin" / ("java.exe" if os.name == "nt" else "java")),
        "java_version": command([home / "bin" / "java", "-version"], capture_output=True, text=True).stderr.strip(),
        "jar": str(jar), "classes": str(classes), "data": str(vendor / "data"),
        "jar_sha256": file_hash(jar), "bridge_sha256": tree_hash(classes),
        "data_sha256": tree_hash(vendor / "data"), "adapter_sha256": file_hash(ROOT / "engine/ArenaMain.java"),
        "build_script_sha256": file_hash(ROOT / "engine/leekscript.init.gradle"),
    }
    write_json(state / "engine.json", metadata)
    return metadata


class Engine:
    def __init__(self, timeout: float = 90):
        if not 0 < timeout <= 3600:
            raise ArenaError("Timeout must be in (0, 3600] seconds")
        self.timeout = timeout
        state = STATE_ROOT / "engine.json"
        if not state.exists():
            raise ArenaError("Engine is not built. Run: python -m arena setup")
        self.metadata = read_json(state)
        m = self.metadata
        if m["lock"] != read_json(ROOT / "engine.lock.json"):
            raise ArenaError("Engine lock changed; rerun setup")
        checks = {
            "jar_sha256": file_hash(Path(m["jar"])), "bridge_sha256": tree_hash(Path(m["classes"])),
            "data_sha256": tree_hash(Path(m["data"])), "adapter_sha256": file_hash(ROOT / "engine/ArenaMain.java"),
            "build_script_sha256": file_hash(ROOT / "engine/leekscript.init.gradle"),
        }
        if any(m[k] != v for k, v in checks.items()):
            raise ArenaError("Engine artifacts changed; rerun setup before starting a new experiment")
        actual_java = command([m["java"], "-version"], capture_output=True, text=True).stderr.strip()
        if actual_java != m["java_version"]:
            raise ArenaError("Java runtime changed; rerun setup")
        self.identity = {k: m[k] for k in ("lock", "java_version", *checks)}
        self.identity["runner_sha256"] = digest({p.relative_to(ROOT).as_posix(): file_hash(p)
                                               for directory in ("arena", "prompts")
                                               for p in sorted((ROOT / directory).rglob("*"))
                                               if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"})
        self.identity["python_version"] = platform.python_version()
        self.identity["platform"] = platform.platform()
        profile = os.environ.get("ARENA_JVM_PROFILE", "startup")
        if profile not in {"startup", "full"}:
            raise ArenaError("ARENA_JVM_PROFILE must be startup or full")
        self.worker_options = ["-Xmx512m", "-Dfile.encoding=UTF-8"]
        if profile == "startup":
            self.worker_options.append("-XX:TieredStopAtLevel=1")
        self.identity["worker_jvm_profile"] = profile
        self.backend = os.environ.get("ARENA_WORKER_BACKEND", "process")
        self.worker_image = os.environ.get("ARENA_WORKER_IMAGE")
        if self.backend not in {"process", "docker"}:
            raise ArenaError("Unknown worker backend")
        if self.backend == "docker" and (not self.worker_image or
                not re.fullmatch(r"(?:[^\s]+@)?sha256:[a-f0-9]{64}", self.worker_image)):
            raise ArenaError("Docker worker requires a pinned ARENA_WORKER_IMAGE digest")
        self.identity["worker_backend"] = {"name": self.backend, "image": self.worker_image if self.backend == "docker" else None}
        self.scientific_identity = {k: v for k, v in self.identity.items()
                                    if k not in {"java_version", "python_version", "platform", "jar_sha256", "bridge_sha256"}}
        self.artifact_provenance = {k: self.identity[k] for k in ("jar_sha256", "bridge_sha256")}
        self.runtime_provenance = {k: self.identity[k] for k in ("java_version", "python_version", "platform")}

    def invoke(self, work: Path, mode: str, argument: str) -> dict:
        shutil.copytree(self.metadata["data"], work / "data")
        classpath = os.pathsep.join([self.metadata["classes"], self.metadata["jar"]])
        args = [self.metadata["java"], *self.worker_options, "-cp", classpath,
                "arena.bridge.ArenaMain", mode, argument, "outcome.json"]
        container = None
        if self.backend == "docker":
            container = "arena-worker-" + uuid4().hex
            args = ["docker", "run", "--rm", "--name", container, "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--memory", "768m", "--cpus", "1", "--pids-limit", "64",
                    "--ulimit", "fsize=8000000:8000000", "--user", f"{os.getuid()}:{os.getgid()}",
                    "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m", "--workdir", "/work",
                    "--mount", f"type=bind,src={work},dst=/work",
                    "--mount", f"type=bind,src={self.metadata['jar']},dst=/engine/generator.jar,readonly",
                    "--mount", f"type=bind,src={self.metadata['classes']},dst=/engine/bridge,readonly",
                    self.worker_image, *self.worker_options, "-cp",
                    "/engine/bridge:/engine/generator.jar", "arena.bridge.ArenaMain", mode, argument, "outcome.json"]
        start = time.monotonic()
        with (work / "stdout.log").open("wb") as stdout, (work / "stderr.log").open("wb") as stderr:
            try:
                allowed = {"PATH", "JAVA_HOME", "SystemRoot", "WINDIR", "TEMP", "TMP",
                           "TMPDIR", "LANG", "LC_ALL", "TZ"}
                environment = {key: value for key, value in os.environ.items() if key in allowed}
                options = {"start_new_session": True, "preexec_fn": worker_limits} if os.name == "posix" else {}
                process = subprocess.Popen(args, cwd=work, stdout=stdout, stderr=stderr,
                                           env=environment, **options)
                try:
                    process.wait(timeout=self.timeout)
                except BaseException:
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        process.kill()
                    process.wait()
                    raise
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "elapsed_seconds": time.monotonic() - start,
                        "error": "Whole-match process deadline exceeded; not attributed to either strategy"}
            finally:
                if container:
                    subprocess.run(["docker", "rm", "-f", container], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        elapsed = time.monotonic() - start
        output = work / "outcome.json"
        if process.returncode or not output.exists():
            return {"status": "engine_error", "elapsed_seconds": elapsed,
                    "error": f"Engine exited {process.returncode}; see stderr.log and outcome.json"}
        try:
            outcome = read_json(output)
        except (ValueError, OSError) as e:
            return {"status": "engine_error", "elapsed_seconds": elapsed, "error": str(e)}
        if "infrastructure_error" in outcome:
            return {"status": "engine_error", "elapsed_seconds": elapsed, "error": outcome["infrastructure_error"]}
        if mode == "analyze":
            return {"status": "valid" if outcome["success"] else "invalid", "elapsed_seconds": elapsed, **outcome}
        if mode == "api":
            return {"status": "exported", **outcome}
        if outcome.get("winner") not in (-1, 0, 1) or not outcome.get("success"):
            return {"status": "engine_error", "elapsed_seconds": elapsed, "error": "Invalid outcome schema"}
        # Timings and debug messages can vary; hash the replay, operations and result.
        replay = {k: outcome[k] for k in ("fight", "winner", "duration")}
        return {
            "status": "completed", "winner_side": outcome["winner"], "turns": outcome["duration"],
            "team_metrics": outcome["team_metrics"], "elapsed_seconds": elapsed,
            "replay_sha256": digest(replay),
            "outcome_sha256": file_hash(output),
        }

    def analyze(self, source: Path, entrypoint: str, out: Path) -> dict:
        info = submission(source, entrypoint)
        out.mkdir(parents=True, exist_ok=False)
        copy_submission(source, out / "strategies/1", info)
        write_json(out / "provenance.json", {"engine": self.identity, "submission": info, "timeout_seconds": self.timeout})
        result = self.invoke(out, "analyze", entrypoint)
        result["source_sha256"] = info["sha256"]
        write_json(out / "result.json", result)
        return result

    def fight(self, sources: list[Path], infos: list[dict], config: dict, seed: int, out: Path) -> dict:
        scenario = make_scenario(config, [s["entrypoint"] for s in infos], seed)
        for key in ("weapons", "chips"):
            known = read_json(Path(self.metadata["data"]) / f"{key}.json")
            for item in config["entity"].get(key, []):
                if str(item) not in known:
                    raise ArenaError(f"Unknown {key} ID in pinned game data: {item}")
        out.mkdir(parents=True, exist_ok=False)
        for side in range(2):
            copy_submission(sources[side], out / f"strategies/{side + 1}", infos[side])
        write_json(out / "scenario.json", scenario)
        write_json(out / "provenance.json", {"engine": self.identity, "submissions": infos,
                   "scenario_sha256": digest(scenario), "timeout_seconds": self.timeout})
        result = self.invoke(out, "fight", "scenario.json")
        write_json(out / "result.json", result)
        return result

    def export_docs(self, out: Path):
        if out.exists():
            raise ArenaError(f"Output already exists: {out}")
        with scratch_directory() as tmp:
            data = self.invoke(tmp, "api", "-")
        if data["status"] != "exported":
            raise ArenaError(f"API export failed: {data}")
        out.mkdir(parents=True)
        write_json(out / "api.json", data)
        lines = ["# LeekScript 4 — API figée de l'arène", "",
                 f"Moteur : `{self.identity['lock']['commit']}`.", "",
                 "Signatures extraites du moteur compilé. Les arguments sont positionnels ; leurs noms et leur sémantique ne sont pas inclus.",
                 "Les coûts indiquent la base déclarée ; 0 ne signifie pas gratuit (coût calculé ailleurs).", "",
                 "## Fonctions", ""]
        for name, f in data["functions"].items():
            lines += [f"### {name}", "", f"Espace : {f['namespace']}. Coût de base déclaré : {f['base_operations']} opérations.", ""]
            lines += [f"- `{name}{signature}`" for signature in f["signatures"]]
            lines.append("")
        lines += ["## Constantes", ""]
        lines += [f"- `{name}` = `{value}`" for name, value in sorted(data["constants"].items())]
        (out / "api.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for name in ("weapons.json", "chips.json", "summons.json", "components.json"):
            shutil.copyfile(Path(self.metadata["data"]) / name, out / name)
        hashes = {p.name: file_hash(p) for p in sorted(out.iterdir()) if p.is_file()}
        write_json(out / "snapshot.json", {"engine": self.identity, "files": hashes})
        return {"status": "exported", "functions": len(data["functions"]), "constants": len(data["constants"])}
