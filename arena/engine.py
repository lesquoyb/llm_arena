from __future__ import annotations

import os
import json
import hashlib
import platform
import signal
import shutil
import subprocess
import sys
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


OUTPUT_LIMIT = 8_000_000


class WorkerOutputLimit(Exception):
    pass


def stop_worker(process):
    """Terminate a worker and its descendants before returning to the caller."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        # taskkill is supplied by Windows; /T also stops any child processes.
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            process.kill()
    process.wait()


def wait_worker(process, work: Path, timeout: float):
    # Poll redirected files on every platform; POSIX additionally has RLIMIT_FSIZE.
    # Polling can overshoot the limit briefly, unlike the POSIX kernel limit.
    deadline = time.monotonic() + timeout
    while True:
        from .activity import poll_provider_failures
        poll_provider_failures()
        if any(p.exists() and p.stat().st_size > OUTPUT_LIMIT
               for p in (work / "stdout.log", work / "stderr.log", work / "outcome.json")):
            raise WorkerOutputLimit("Worker output exceeded 8 MB per file")
        if process.poll() is not None:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        try:
            process.wait(timeout=min(0.05, remaining))
        except subprocess.TimeoutExpired:
            pass


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
    gradle_args = [gradle]
    if os.name == "nt" and Path(gradle).suffix.lower() in {".bat", ".cmd"}:
        # Launch the standard Gradle distribution directly, without cmd.exe quoting.
        launcher = Path(gradle).resolve().parent.parent / "lib" / f"gradle-gradle-cli-main-{lock['gradle_version']}.jar"
        if not launcher.is_file():
            raise ArenaError("Use the standard Gradle distribution or scripts/bootstrap.py")
        gradle_args = [home / "bin/java.exe", "-Dorg.gradle.appname=gradle", "-jar", launcher]
    version = capture([*gradle_args, "--version"])
    if f"Gradle {lock['gradle_version']}" not in version:
        raise ArenaError(f"Gradle {lock['gradle_version']} is required for the pinned build")
    command([*gradle_args, f"-Dorg.gradle.java.home={home}", "--no-daemon", "--init-script", ROOT / "engine/leekscript.init.gradle", "jar"], vendor)
    state = STATE_ROOT
    classes = state / "bridge"
    classes.mkdir(parents=True, exist_ok=True)
    jar = vendor / "generator.jar"
    command([home / "bin" / ("javac.exe" if os.name == "nt" else "javac"), "-encoding", "UTF-8", "-cp", jar, "-d", classes, ROOT / "engine/ArenaMain.java", ROOT / "engine/ArenaWorker.java"])
    metadata = {
        "lock": lock, "java": str(home / "bin" / ("java.exe" if os.name == "nt" else "java")),
        "java_version": command([home / "bin" / ("java.exe" if os.name == "nt" else "java"), "-version"], capture_output=True, text=True).stderr.strip(),
        "jar": str(jar), "classes": str(classes), "data": str(vendor / "data"),
        "jar_sha256": file_hash(jar), "bridge_sha256": tree_hash(classes),
        "data_sha256": tree_hash(vendor / "data"), "adapter_sha256": file_hash(ROOT / "engine/ArenaMain.java"),
        "worker_transport_sha256": file_hash(ROOT / "engine/ArenaWorker.java"),
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
        if 'worker_transport_sha256' in m:checks['worker_transport_sha256']=file_hash(ROOT/'engine/ArenaWorker.java')
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
        self.identity["build_rules_sha256"] = digest({name: file_hash(ROOT / 'docs/corpus' / name)
            for name in ('stat-rules.json', 'component-rules.json')})
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
        mode=os.environ.get('ARENA_JVM_MODE','pooled')
        if mode not in {'pooled','isolated'}:raise ArenaError('ARENA_JVM_MODE must be pooled or isolated')
        available=(Path(self.metadata['classes'])/'arena/bridge/ArenaWorker.class').is_file()
        self._jvm_pool=None
        self.identity['worker_execution']='pooled-classloader' if mode=='pooled' and available and self.backend=='process' else 'isolated'
        if self.identity['worker_execution']=='pooled-classloader':
            from .jvm_pool import Pool
            self._jvm_pool=Pool(self)
        self.scientific_identity = {k: v for k, v in self.identity.items()
                                    if k not in {"java_version", "python_version", "platform", "jar_sha256", "bridge_sha256", "worker_execution", "worker_transport_sha256"}}
        self.artifact_provenance = {k: self.identity[k] for k in ("jar_sha256", "bridge_sha256")}
        self.runtime_provenance = {k: self.identity[k] for k in ("java_version", "python_version", "platform")}

    def close(self):
        if getattr(self,'_jvm_pool',None):self._jvm_pool.close()

    def invoke(self, work: Path, mode: str, argument: str) -> dict:
        from .fight_phases import phase
        started=time.monotonic();timings={}
        try:result=self._invoke(work,mode,argument,timings)
        finally:
            phase('cleanup_data');cleanup=time.monotonic()
            try:shutil.rmtree(work/'data')
            except FileNotFoundError:pass
            except OSError:timings['data_cleanup_failed']=True  # Retain a still-open temporary input for inspection.
            timings['data_cleanup_seconds']=time.monotonic()-cleanup
        timings['invocation_seconds']=time.monotonic()-started
        if mode!='api':result['timings']=timings
        return result

    def _invoke(self, work: Path, mode: str, argument: str, timings: dict) -> dict:
        from .fight_phases import phase
        if mode=='fight' and getattr(self,'_jvm_pool',None):
            started=time.monotonic()
            try:
                code=self._jvm_pool.run(work,mode,argument,timings)
            except (OSError,subprocess.TimeoutExpired,WorkerOutputLimit) as error:
                from .worker_resources import host_memory,log_tail
                return {'status':'timeout' if isinstance(error,subprocess.TimeoutExpired) else 'engine_error',
                    'elapsed_seconds':time.monotonic()-started,'error':str(error),
                    'failure_details':{'phase':'pooled_jvm','host_memory':host_memory(),'stderr_tail':log_tail(work/'stderr.log')}}
            return self._read_outcome(work,mode,time.monotonic()-started,code,timings)
        phase('staging_data');staging=time.monotonic()
        timings.update(data_hardlinked_files=0,data_copied_files=0,data_copied_bytes=0)
        def link_or_copy(source,target):
            # Pinned engine data are read-only inputs. Hardlinks avoid copying
            # their bytes for every JVM; other volumes/filesystems fall back.
            try:
                os.link(source,target);timings['data_hardlinked_files']+=1;return target
            except OSError:
                timings['data_copied_files']+=1;timings['data_copied_bytes']+=Path(source).stat().st_size
                return shutil.copy2(source,target)
        shutil.copytree(self.metadata["data"], work / "data",copy_function=link_or_copy)
        timings['data_staging_seconds']=time.monotonic()-staging
        classpath = os.pathsep.join([self.metadata["classes"], self.metadata["jar"]])
        args = [self.metadata["java"], *self.worker_options, "-cp", classpath,
                "arena.bridge.ArenaMain", mode, argument, "outcome.json"]
        container = None
        if self.backend == "docker":
            container = "arena-worker-" + uuid4().hex
            args = ["docker", "run", "--rm", "--name", container, "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--memory", "768m", "--cpus", "1", "--pids-limit", "64",
                    "--ulimit", "fsize=8000000:8000000", "--user", (f"{os.getuid()}:{os.getgid()}" if os.name == "posix" else "65534:65534"),
                    "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m", "--workdir", "/work",
                    "--mount", f"type=bind,src={work},dst=/work",
                    "--mount", f"type=bind,src={self.metadata['jar']},dst=/engine/generator.jar,readonly",
                    "--mount", f"type=bind,src={self.metadata['classes']},dst=/engine/bridge,readonly",
                    self.worker_image, *self.worker_options, "-cp",
                    "/engine/bridge:/engine/generator.jar", "arena.bridge.ArenaMain", mode, argument, "outcome.json"]
        phase('engine');start = time.monotonic()
        with (work / "stdout.log").open("wb") as stdout, (work / "stderr.log").open("wb") as stderr:
            try:
                allowed = {"PATH", "JAVA_HOME", "SystemRoot", "WINDIR", "TEMP", "TMP",
                           "TMPDIR", "LANG", "LC_ALL", "TZ"}
                environment = {key: value for key, value in os.environ.items() if key.upper() in {name.upper() for name in allowed}}
                options = {"start_new_session": True} if os.name == "posix" else {}
                if os.name=='posix':
                    args=[sys.executable,str(Path(__file__).with_name('worker_limits.py')),*args]
                try:
                    process = subprocess.Popen(args, cwd=work, stdout=stdout, stderr=stderr,
                                               env=environment, **options)
                except OSError as error:
                    from .worker_resources import host_memory
                    return {'status':'engine_error','elapsed_seconds':time.monotonic()-start,
                            'error':'Engine process could not start: '+str(error),
                            'failure_details':{'phase':'process_launch','errno':error.errno,'winerror':getattr(error,'winerror',None),'host_memory':host_memory()}}
                try:
                    wait_worker(process, work, self.timeout)
                except BaseException:
                    stop_worker(process)
                    raise
            except WorkerOutputLimit as error:
                return {"status": "engine_error", "elapsed_seconds": time.monotonic() - start,
                        "error": str(error)}
            except subprocess.TimeoutExpired:
                from .worker_resources import host_memory, log_tail
                return {"status": "timeout", "elapsed_seconds": time.monotonic() - start,
                        "error": "Whole-match process deadline exceeded; not attributed to either strategy",
                        'failure_details':{'phase':'process_timeout','deadline_seconds':self.timeout,'host_memory':host_memory(),
                                           'stderr_tail':log_tail(work/'stderr.log'),'stdout_tail':log_tail(work/'stdout.log')}}
            finally:
                timings['java_process_seconds']=time.monotonic()-start
                if 'process' in locals():
                    from .worker_resources import process_cpu_seconds
                    cpu=process_cpu_seconds(process)
                    if cpu is not None:timings['java_cpu_seconds']=cpu
                if container:
                    subprocess.run(["docker", "rm", "-f", container], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return self._read_outcome(work,mode,time.monotonic()-start,process.returncode,timings)

    def _read_outcome(self, work, mode, elapsed, returncode, timings):
        from .fight_phases import phase
        phase('reading_result');reading=time.monotonic()
        output = work / "outcome.json"
        if returncode or not output.exists():
            from .worker_resources import host_memory, log_tail
            return {"status": "engine_error", "elapsed_seconds": elapsed,
                    "error": f"Engine exited {returncode}; see stderr.log and outcome.json",
                    'failure_details':{'phase':'process_exit','exit_code':returncode,'host_memory':host_memory(),
                                       'stderr_tail':log_tail(work/'stderr.log'),'stdout_tail':log_tail(work/'stdout.log')}}
        try:
            outcome_bytes=output.read_bytes()
            outcome=json.loads(outcome_bytes)
            outcome_hash=hashlib.sha256(outcome_bytes).hexdigest()
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
        result = {
            "status": "completed", "winner_side": outcome["winner"], "turns": outcome["duration"],
            "team_metrics": outcome["team_metrics"], "elapsed_seconds": elapsed,
            "replay_sha256": digest(replay),
            "outcome_sha256": outcome_hash,
        }
        timings['result_read_seconds']=time.monotonic()-reading
        return result

    def analyze(self, source: Path, entrypoint: str, out: Path) -> dict:
        info = submission(source, entrypoint)
        out.mkdir(parents=True, exist_ok=False)
        copy_submission(source, out / "strategies/1", info)
        write_json(out / "provenance.json", {"engine": self.identity, "submission": info, "timeout_seconds": self.timeout})
        if info.get('configuration_error'):
            result={'status':'invalid','success':False,'phase':'team_configuration','diagnostics':[{'severity':'error','file':'team.json','message':info['configuration_error']}],'source_sha256':info['sha256']}
            write_json(out/'result.json',result)
            return result
        result = self.invoke(out, "analyze", entrypoint)
        member_results = {}
        entries = sorted({member["entrypoint"] for member in info.get("team", {}).get("members", [])} - {entrypoint})
        for index, member_entry in enumerate(entries):
            work = out / "member-analysis" / str(index)
            member_info = submission(source, member_entry)
            copy_submission(source, work / "strategies/1", member_info)
            write_json(work / "provenance.json", {"engine": self.identity, "submission": member_info,
                       "timeout_seconds": self.timeout})
            assessment = self.invoke(work, "analyze", member_entry)
            write_json(work / "result.json", assessment)
            member_results[member_entry] = assessment
        if member_results:
            result["member_analyses"] = member_results
            statuses = [result["status"], *[r["status"] for r in member_results.values()]]
            result["status"] = "engine_error" if "engine_error" in statuses else "invalid" if "invalid" in statuses else "valid"
            result["success"] = result["status"] == "valid"
        result["source_sha256"] = info["sha256"]
        write_json(out / "result.json", result)
        return result

    def fight(self, sources: list[Path], infos: list[dict], config: dict, seed: int, out: Path) -> dict:
        from .fight_phases import phase
        phase('preparing');started=time.monotonic()
        scenario = make_scenario(config, [s["entrypoint"] for s in infos], seed, [s.get("team") for s in infos])
        from .teams import validate_team
        for info in infos:
            if info.get("team"):
                validate_team(info["team"], config, info["files"], Path(self.metadata["data"]))
        for key in ("weapons", "chips"):
            from .equipment import catalog
            known = catalog(Path(self.metadata["data"]), key)
            for team in scenario["entities"]:
                for entity in team:
                    for item in entity.get(key, []):
                        if str(item) not in known:
                            raise ArenaError(f"Unknown {key} ID in pinned game data: {item}")
                        if config.get("stats_mode") == "realistic-v1" and known[str(item)].get("level", 1) > entity["level"]:
                            raise ArenaError(f"{key} ID {item} requires level {known[str(item)]['level']}; leek level is {entity['level']}")
        out.mkdir(parents=True, exist_ok=False)
        for side in range(2):
            copy_submission(sources[side], out / f"strategies/{side + 1}", infos[side])
        write_json(out / "scenario.json", scenario)
        write_json(out / "provenance.json", {"engine": self.identity, "submissions": infos,
                   "scenario_sha256": digest(scenario), "timeout_seconds": self.timeout})
        snapshot_seconds=time.monotonic()-started
        missing_team=[side for side,info in enumerate(infos) if info.get('configuration_error')]
        if missing_team:
            winner=-1 if len(missing_team)==2 else 1-missing_team[0]
            metrics={str(side):{'operations':0,'errors':int(side in missing_team),'operation_limit_hits':0} for side in range(2)}
            outcome={'success':True,'winner':winner,'duration':0,'fight':{'actions':[],'leeks':[]},'logs':{},'team_metrics':metrics,
                     'forfeit':True,'configuration_errors':{str(side):infos[side]['configuration_error'] for side in missing_team}}
            write_json(out/'outcome.json',outcome)
            result={'status':'completed','winner_side':winner,'turns':0,'team_metrics':metrics,'elapsed_seconds':0,
                    'forfeit':True,'configuration_errors':outcome['configuration_errors'],
                    'replay_sha256':digest({k:outcome[k] for k in ('fight','winner','duration')}),'outcome_sha256':file_hash(out/'outcome.json')}
        else:
            result = self.invoke(out, "fight", "scenario.json")
        phase('archiving_result')
        result['timings']={**result.get('timings',{}),'scenario_and_sources_seconds':snapshot_seconds,
                           'fight_wall_seconds':time.monotonic()-started}
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
        lines = ["# LeekScript 4 API reference", "",
                 f"Engine: `{self.identity['lock']['commit']}`.", "",
                 "Signatures extracted from the compiled engine. Arguments are positional; names and behavior are not included.",
                 "Costs are declared base costs. Zero does not mean free; some costs are calculated elsewhere.", "",
                 "## Functions", ""]
        for name, f in data["functions"].items():
            lines += [f"### {name}", "", f"Namespace: {f['namespace']}. Declared base cost: {f['base_operations']} operations.", ""]
            lines += [f"- `{name}{signature}`" for signature in f["signatures"]]
            lines.append("")
        lines += ["## Constants", ""]
        lines += [f"- `{name}` = `{value}`" for name, value in sorted(data["constants"].items())]
        (out / "api.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for name in ("weapons.json", "chips.json", "summons.json", "components.json"):
            shutil.copyfile(Path(self.metadata["data"]) / name, out / name)
        hashes = {p.name: file_hash(p) for p in sorted(out.iterdir()) if p.is_file()}
        write_json(out / "snapshot.json", {"engine": self.identity, "files": hashes})
        return {"status": "exported", "functions": len(data["functions"]), "constants": len(data["constants"])}
