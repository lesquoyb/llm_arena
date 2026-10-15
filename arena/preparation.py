"""Common local preparation tools restricted to a single session."""
from __future__ import annotations

from pathlib import Path
import json
import re
from uuid import uuid4

from .core import ArenaError, ROOT, copy_submission, file_hash, read_json, submission, write_json


def local_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ArenaError("Expected a relative path")
    path = root / name
    if ".." in Path(name).parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ArenaError("Traversal and links are not allowed")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ArenaError("Path escapes session")
    return path


class Preparation:
    def __init__(self, directory: Path, docs: Path, engine, scenario: dict):
        self.directory, self.docs = directory, docs
        self.workspace = directory / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.engine, self.scenario = engine, scenario

    def call(self, name: str, arguments: dict, call_id: str) -> dict:
        if not re.fullmatch(r"call-[0-9]+-tool-[0-9]+", call_id) and call_id not in {"final"} and not call_id.isdigit():
            raise ArenaError("Invalid internal call ID")
        if not isinstance(arguments, dict):
            raise ArenaError("Tool arguments must be an object")
        entry = arguments.get("entrypoint", "main.leek")
        if name == "list_files":
            self._fields(arguments, set())
            return {"files": sorted(p.relative_to(self.workspace).as_posix()
                                   for p in self.workspace.rglob("*.leek") if p.is_file())}
        if name in {"read_file", "read_docs"}:
            self._fields(arguments, {"path", "offset", "limit"})
            root = self.docs if name == "read_docs" else self.workspace
            text = local_path(root, arguments["path"]).read_text(encoding="utf-8")
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
            existing = [p for p in self.workspace.rglob("*.leek") if p.is_file() and p != path]
            if len(existing) >= 128 or sum(p.stat().st_size for p in existing) + len(encoded) > 2_000_000:
                raise ArenaError("Submission quota exceeded")
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".leek.tmp")
            tmp.write_bytes(encoded)
            tmp.replace(path)
            return {"sha256": file_hash(path)}
        if name == "read_replay":
            self._fields(arguments, {"test_id", "side", "section", "offset", "limit"})
            test_id = arguments["test_id"]
            side = arguments.get("side", 0)
            section = arguments.get("section", "fight")
            if (not isinstance(test_id, str) or not re.fullmatch(r"call-[0-9]+-tool-[0-9]+", test_id)
                    or type(side) is not int or side not in (0, 1)
                    or section not in {"fight", "team_metrics"}):
                raise ArenaError("Invalid replay reference")
            base = self.directory / "tools" / f"{test_id}-side-{side}"
            cached = read_json(base / "cached.json")
            outcome = read_json(local_path(self.directory, cached["artifact_dir"]) / "outcome.json")
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
