"""Common local preparation tools restricted to a single session."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
import json
import re
from uuid import uuid4

from .core import ArenaError, ROOT, copy_submission, file_hash, is_link, read_json, replace_file, submission, write_json


def local_path(root: Path, name: str) -> Path:
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or PureWindowsPath(name).anchor or ":" in name
            or any(re.match(r"(?i)(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)",
                            part.rstrip(" .")) for part in PureWindowsPath(name).parts)):
        raise ArenaError("Expected a relative path")
    path = root / name
    if (".." in PureWindowsPath(name).parts or ".." in Path(name).parts
            or any(is_link(p)
                   for p in [path, *path.parents])):
        raise ArenaError("Traversal and links are not allowed")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ArenaError("Path escapes session")
    return path


class Preparation:
    def __init__(self, directory: Path, docs: Path, engine, scenario: dict, feedback=None):
        self.directory, self.docs = directory, docs
        self.workspace = directory / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.engine, self.scenario = engine, scenario
        self.feedback = feedback

    def call(self, name: str, arguments: dict, call_id: str) -> dict:
        if not re.fullmatch(r"call-[0-9]+-tool-[0-9]+", call_id) and call_id not in {"final"} and not call_id.isdigit():
            raise ArenaError("Invalid internal call ID")
        if not isinstance(arguments, dict):
            raise ArenaError("Tool arguments must be an object")
        from .feedback import FEEDBACK_NAMES
        if name in FEEDBACK_NAMES:
            if self.feedback is None:
                raise ArenaError("Past tournament fights are forbidden without feedback access")
            return self.feedback.call(name, arguments)
        entry = arguments.get("entrypoint", "main.leek")
        if name == "list_files":
            self._fields(arguments, set())
            return {"files": sorted(p.relative_to(self.workspace).as_posix()
                                   for p in self.workspace.rglob("*") if p.is_file() and (p.suffix == ".leek" or p == self.workspace / "team.json"))}
        if name in {"read_file", "read_docs"}:
            self._fields(arguments, {"path", "offset", "limit"})
            root = self.docs if name == "read_docs" else self.workspace
            text = local_path(root, arguments["path"]).read_text(encoding="utf-8")
            if name == "read_docs" and local_path(root, arguments["path"]) == root / "leekscript-v1/chips.json":
                from .equipment import SPECIAL_CHIPS
                text = json.dumps({key: row for key, row in json.loads(text).items()
                                   if int(key) not in SPECIAL_CHIPS}, ensure_ascii=False, indent=2)
            offset, limit = arguments.get("offset", 0), arguments.get("limit", 4000)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
                raise ArenaError("Invalid page")
            end = offset + limit
            return {"content": text[offset:end], "truncated": end < len(text),
                    "next_offset": end if end < len(text) else None}
        if name == "write_file":
            self._fields(arguments, {"path", "content"})
            path = local_path(self.workspace, arguments["path"])
            content = arguments["content"]
            if path.suffix != ".leek" or not isinstance(content, str):
                raise ArenaError("Only text .leek files are allowed")
            encoded = content.encode("utf-8")
            existing = [p for p in self.workspace.rglob("*") if p.is_file() and (p.suffix == ".leek" or p == self.workspace / "team.json") and p != path]
            if len(existing) >= 128 or sum(p.stat().st_size for p in existing) + len(encoded) > 2_000_000:
                raise ArenaError("Submission quota exceeded")
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".leek.tmp")
            tmp.write_bytes(encoded)
            replace_file(tmp, path)
            return {"sha256": file_hash(path)}
        if name == "preview_build":
            from .teams import build_preview
            self._fields(arguments, {"capital", "member_index", "components", "level"})
            try:
                return {"valid": True, **build_preview(self.scenario, arguments.get("member_index", 0), arguments.get("capital"), arguments.get("components"), arguments.get('level'))}
            except ArenaError as error:
                return {"valid": False, "errors": [str(error)]}
        if name == "validate_team":
            from .teams import validate_team, team_preview
            from .core import source_files
            self._fields(arguments, {"members"})
            if not self.scenario.get("team_selection"):
                raise ArenaError("Participant teams are disabled for this competition")
            try:
                team = validate_team(arguments, self.scenario, None, self.docs / "leekscript-v1")
                return team_preview(team, self.scenario, {p.relative_to(self.workspace).as_posix() for p in self.workspace.rglob("*.leek") if p.is_file()})
            except ArenaError as error:
                return {"valid": False, "errors": [str(error)]}
        if name == "configure_team":
            from .teams import TEAM_FILE, validate_team, team_preview
            from .core import source_files
            self._fields(arguments, {"members"})
            if not self.scenario.get("team_selection"):
                raise ArenaError("Participant teams are disabled for this competition")
            team = validate_team(arguments, self.scenario, source_files(self.workspace), self.docs / "leekscript-v1")
            write_json(self.workspace / TEAM_FILE, team)
            return {"path": TEAM_FILE, "content": (self.workspace / TEAM_FILE).read_text(encoding="utf-8"),
                    "sha256": file_hash(self.workspace / TEAM_FILE), "team": team,
                    "validation": team_preview(team, self.scenario, source_files(self.workspace), check_sources=True)}
        if name == "read_replay":
            self._fields(arguments, {"test_id", "side", "section", "offset", "limit"})
            test_id = arguments["test_id"]
            side = arguments.get("side", 0)
            section = arguments.get("section", "fight")
            if (not isinstance(test_id, str) or not re.fullmatch(r"call-[0-9]+-tool-[0-9]+", test_id)
                    or type(side) is not int or side not in (0, 1)
                    or section not in {"fight", "team_metrics", "turn_metrics", "logs"}):
                raise ArenaError("Invalid replay reference")
            base = self.directory / "tools" / f"{test_id}-side-{side}"
            cached = read_json(base / "cached.json")
            outcome = read_json(local_path(self.directory, cached["artifact_dir"]) / "outcome.json")
            if section not in outcome:
                raise ArenaError("This archive has no " + section + " section")
            text = json.dumps(outcome[section], ensure_ascii=False)
            offset, limit = arguments.get("offset", 0), arguments.get("limit", 4000)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
                raise ArenaError("Invalid page")
            return {"content": text[offset:offset + limit], "truncated": offset + limit < len(text),
                    "next_offset": offset + limit if offset + limit < len(text) else None}
        if name in {"analyze", "test", "submit"}:
            self._fields(arguments, {"entrypoint", "scenario_id", "seed_id", "opponent_id"} if name == "test" else {"entrypoint"})
            if name == "test" and (arguments.get("scenario_id", "training") != "training" or
                                   arguments.get("seed_id", "train-17") != "train-17" or
                                   arguments.get("opponent_id", "passive") != "passive"):
                raise ArenaError("Test is outside the preparation catalog")
            info = submission(self.workspace, entry)
            if self.scenario.get("team_selection") and name in {"test", "submit"}:
                from .teams import validate_team
                if "team" not in info:
                    raise ArenaError("Choose a team with configure_team before testing or submitting")
                validate_team(info["team"], self.scenario, info["files"], self.docs / "leekscript-v1")
            if name == "submit":
                target = self.directory / "submission"
                if target.exists():
                    if submission(target, entry) != info:
                        raise ArenaError("Frozen submission changed")
                else:
                    staging = self.directory / f"submission-staging-{uuid4().hex}"
                    copy_submission(self.workspace, staging, info)
                    staging.rename(target)
                return {"submission": info}
            if name == "analyze":
                out = self.directory / "tools" / call_id
                if (out / "result.json").exists():
                    if read_json(out / "provenance.json")["submission"] != info:
                        raise ArenaError("Cached analysis source differs from current source")
                    return read_json(out / "result.json")
                # An interrupted invocation is retained; retry in a new directory.
                out = self._attempt(out)
                return self.engine.analyze(self.workspace, entry, out)
            opponent = ROOT / "examples/strategies/passive"
            results = []
            for side in range(2):
                base = self.directory / "tools" / f"{call_id}-side-{side}"
                cached = base / "cached.json"
                if cached.exists():
                    results.append(read_json(cached))
                    continue
                sources = [self.workspace, opponent] if side == 0 else [opponent, self.workspace]
                infos = [submission(s, entry if s == self.workspace else "main.leek") for s in sources]
                work = self._attempt(base / "match")
                result = self.engine.fight(sources, infos, self.scenario, 17, work)
                result["artifact_dir"] = work.relative_to(self.directory).as_posix()
                write_json(cached, result)
                results.append(result)
            return {"test_id": call_id, "training_seed": 17, "opponent": "passive", "matches": results}
        raise ArenaError("Unknown tool")

    @staticmethod
    def _fields(arguments, allowed):
        if set(arguments) - allowed:
            raise ArenaError("Unsupported tool arguments")

    @staticmethod
    def _attempt(base):
        out = base
        index = 1
        while out.exists():
            out = base.with_name(base.name + f"-retry-{index}")
            index += 1
        return out
