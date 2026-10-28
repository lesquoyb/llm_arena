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
    def __init__(self, directory: Path, docs: Path, engine, scenario: dict, feedback=None, allowed_tools=None, versions=None):
        self.directory, self.docs = directory, docs
        self.workspace = directory / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.engine, self.scenario = engine, scenario
        self.feedback = feedback
        self.allowed_tools = allowed_tools
        self.versions = versions

    def _archive(self, info):
        target=self.directory/'submission'
        if target.exists():
            if submission(target,info['entrypoint'])!=info: raise ArenaError('Frozen submission changed')
        else:
            staging=self.directory/f'submission-staging-{uuid4().hex}'
            copy_submission(self.workspace,staging,info);staging.rename(target)
        return {'submission':info}

    def freeze_latest(self, entrypoint=None):
        """Budget closure freezes saved sources; missing team remains an invalid entry."""
        from .core import source_files
        files=source_files(self.workspace)
        if not entrypoint or entrypoint not in files:
            if 'team.json' in files:
                members=read_json(self.workspace/'team.json').get('members',[])
                entrypoint=members[0]['entrypoint'] if members else None
            if not entrypoint:
                choices=[name for name in files if name.endswith('.leek')]
                entrypoint='main.leek' if 'main.leek' in files else choices[0] if len(choices)==1 else None
        if not entrypoint: raise ArenaError('Several source files exist but no main.leek or configured entrypoint identifies the program')
        try: return self.call('submit',{'entrypoint':entrypoint},'final')
        except ArenaError:
            info=submission(self.workspace,entrypoint)
            if self.scenario.get('team_selection') and 'team' not in info:
                error='Sources were frozen at the preparation limit, but no team was configured. Call configure_team with members, entrypoints, equipment and required capital before the next submission.'
                from .core import AUTOMATIC_ERROR_FILE
                write_json(self.workspace/AUTOMATIC_ERROR_FILE,{'error':error})
                result=self._archive(submission(self.workspace,entrypoint));result['configuration_error']=error
                return result
            raise

    def call(self, name: str, arguments: dict, call_id: str) -> dict:
        if self.allowed_tools is not None and name not in self.allowed_tools:
            raise ArenaError("Tool is disabled for this calibration trial")
        if not re.fullmatch(r"call-[0-9]+-tool-[0-9]+", call_id) and call_id not in {"final"} and not call_id.isdigit():
            raise ArenaError("Invalid internal call ID")
        if not isinstance(arguments, dict):
            raise ArenaError("Tool arguments must be an object")
        from .feedback import FEEDBACK_NAMES
        if name in FEEDBACK_NAMES:
            if self.feedback is None:
                raise ArenaError("Past tournament fights are forbidden without feedback access")
            return self.feedback.call(name, arguments)
        if name in {'list_submissions','read_submitted_file'}:
            if self.versions is None: raise ArenaError('Submitted versions are not available in this session')
            return self.versions.call(name, arguments)
        entry = arguments.get("entrypoint", "main.leek")
        if name == "lookup_api":
            self._fields(arguments, {'query','queries','mode','kind','offset','limit'})
            from .api_lookup import lookup
            return lookup(read_json(self.docs/'leekscript-v1/api.json'),arguments)
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
            if name == "read_docs":
                from .model_content import documentation
                text = documentation(arguments["path"], text)
            from .model_content import character_page
            offset, limit = character_page(arguments)
            end = min(offset + limit, len(text))
            next_offset = end if end < len(text) else None
            return {"path": arguments["path"], "offset": offset, "end_offset": max(offset, end),
                    "total_characters": len(text), "returned_characters": len(text[offset:end]),
                    "content": text[offset:end], "truncated": next_offset is not None,
                    "next_offset": next_offset,
                    "reading_status": "partial" if next_offset is not None else "end_of_file",
                    "continuation": ({"tool": name, "arguments": {"path": arguments["path"], "offset": next_offset, "limit": limit}}
                                     if next_offset is not None else None)}
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
            created = not path.exists()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".leek.tmp")
            tmp.write_bytes(encoded)
            replace_file(tmp, path)
            return {"path": arguments["path"], "characters": len(content), "bytes": len(encoded),
                    "created": created, "sha256": file_hash(path)}
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
            from .core import AUTOMATIC_ERROR_FILE
            (self.workspace/AUTOMATIC_ERROR_FILE).unlink(missing_ok=True)
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
            from .model_content import compact, page
            text = compact(outcome[section])
            return page(text, arguments, 'read_replay', {'test_id':test_id,'side':side,'section':section})
        if name in {"analyze", "test", "submit"}:
            self._fields(arguments, {"entrypoint", "scenario_id", "seed_id", "opponent_id", "opponent_entrypoint"} if name == "test" else {"entrypoint"})
            own_opponent = arguments.get('opponent_entrypoint')
            opponent_id = arguments.get('opponent_id', 'workspace' if own_opponent is not None else 'passive')
            if name == 'test':
                if (arguments.get('scenario_id','training') != 'training' or arguments.get('seed_id','train-17') != 'train-17'
                        or opponent_id not in {'passive','workspace'}):
                    raise ArenaError('Test is outside the preparation catalog')
                if (opponent_id == 'workspace') != (own_opponent is not None):
                    raise ArenaError('Choose opponent_entrypoint for a workspace opponent, or omit it for passive')
            info = submission(self.workspace, entry)
            if self.scenario.get("team_selection") and name in {"test", "submit"}:
                from .teams import validate_team
                if "team" not in info:
                    raise ArenaError("Choose a team with configure_team before testing or submitting")
                validate_team(info["team"], self.scenario, info["files"], self.docs / "leekscript-v1")
            if name == "submit":
                return self._archive(info)
            if name == "analyze":
                out = self.directory / "tools" / call_id
                from .compiler_diagnostics import readable_analysis
                if (out / "result.json").exists():
                    if read_json(out / "provenance.json")["submission"] != info:
                        raise ArenaError("Cached analysis source differs from current source")
                    return readable_analysis(read_json(out / "result.json"), getattr(self.engine, "identity", None), self.workspace)
                # An interrupted invocation is retained; retry in a new directory.
                out = self._attempt(out)
                from .activity import operation, session_root
                with operation(session_root(self.directory),'preparation_analysis',participants=[self.directory.name]):
                    return readable_analysis(self.engine.analyze(self.workspace, entry, out), getattr(self.engine, "identity", None), self.workspace)
            opponent = ROOT / 'examples/strategies/passive'
            opponent_info = submission(opponent,'main.leek')
            if own_opponent is not None:
                # Resolve only this model's source files; no arbitrary opponent paths.
                local_path(self.workspace, own_opponent)
                opponent = self.workspace
                opponent_info = submission(opponent,own_opponent)
                if 'team' in opponent_info:
                    # Test the alternate script on the same roster, without changing
                    # the candidate's configured member entrypoints or team.json.
                    import copy
                    from .teams import TEAM_FILE, validate_team
                    from .core import source_files
                    target = self.directory/'tools'/f'{call_id}-opponent'
                    if not target.exists():
                        staging = target.with_name(target.name+'-staging-'+uuid4().hex)
                        copy_submission(self.workspace,staging,opponent_info)
                        team = copy.deepcopy(opponent_info['team'])
                        for member in team['members']: member['entrypoint'] = own_opponent
                        team = validate_team(team,self.scenario,source_files(staging),self.docs/'leekscript-v1')
                        write_json(staging/TEAM_FILE,team)
                        staging.rename(target)
                    opponent = target
                    opponent_info = submission(opponent,own_opponent)
            results = []
            for side in range(2):
                base = self.directory / "tools" / f"{call_id}-side-{side}"
                cached = base / "cached.json"
                if cached.exists():
                    results.append(read_json(cached))
                    continue
                sources = [self.workspace, opponent] if side == 0 else [opponent, self.workspace]
                infos = [info,opponent_info] if side == 0 else [opponent_info,info]
                work = self._attempt(base / "match")
                from .activity import operation, session_root
                with operation(session_root(self.directory),'preparation_fight',participants=[self.directory.name],
                               opponent=opponent_id,side=side):
                    result = self.engine.fight(sources, infos, self.scenario, 17, work)
                result["artifact_dir"] = work.relative_to(self.directory).as_posix()
                result['own_side'] = side
                result['opponent'] = opponent_id
                if own_opponent is not None: result['opponent_entrypoint'] = own_opponent
                write_json(cached, result)
                results.append(result)
            return {"test_id": call_id, "training_seed": 17, "entrypoint":entry,"opponent":opponent_id,
                    **({'opponent_entrypoint':own_opponent, 'opponent_roster':'Same roster; every opposing member runs opponent_entrypoint'} if own_opponent is not None else {}),
                    "matches": results}
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
