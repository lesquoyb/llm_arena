"""Versioned artifacts and strict validation for the local arena."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
import os
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(os.environ.get("ARENA_PROJECT_ROOT", Path(__file__).resolve().parent.parent)).resolve()
STATE_ROOT = Path(os.environ.get("ARENA_STATE_ROOT", ROOT / ".arena")).resolve()
DEFAULT_SCENARIO = {
    "team_size": 2,
    "max_turns": 32,
    "entity": {
        "level": 100, "life": 600, "strength": 100, "agility": 0,
        "frequency": 100, "tp": 12, "mp": 5, "cores": 10, "ram": 10,
        "weapons": [37], "chips": [],
    },
}


class ArenaError(Exception):
    pass


def is_link(path: Path) -> bool:
    """Also reject Windows junctions/reparse points, including on Python 3.11."""
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


@contextmanager
def file_lock(path: Path):
    """Non-blocking OS lock, released even when the owning process crashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            # Windows byte-range locks need a stable byte, including in a new file.
            if stream.seek(0, os.SEEK_END) == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            acquire = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(stream, fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as error:
            import errno
            if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            raise ArenaError("Another process is writing these artifacts") from error
        try:
            yield
        finally:
            release()


@contextmanager
def scratch_directory():
    # Keep temporary artifacts inside the workspace, including under Windows sandboxing.
    base = (STATE_ROOT / "tmp").resolve()
    path = base / uuid.uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        resolved = path.resolve()
        if resolved.parent != base or is_link(path):
            raise ArenaError(f"Refusing to clean up unexpected temporary path: {path}")
        shutil.rmtree(resolved)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(path: Path) -> str:
    return digest({p.relative_to(path).as_posix(): file_hash(p) for p in sorted(path.rglob("*")) if p.is_file()})


def source_files(source: Path) -> dict[str, bytes]:
    if not source.is_dir() or is_link(source):
        raise ArenaError(f"Submission must be a directory, not a link: {source}")
    files = {}
    for p in sorted(source.rglob("*")):
        if is_link(p):
            raise ArenaError(f"Links are not allowed in submissions: {p}")
        if p.is_file() and p.suffix == ".leek":
            files[p.relative_to(source).as_posix()] = p.read_bytes()
    if not files or len(files) > 128 or sum(map(len, files.values())) > 2_000_000:
        raise ArenaError("A submission must contain 1–128 .leek files, totalling at most 2 MB")
    return files


def submission(source: Path, entrypoint: str = "main.leek") -> dict:
    files = source_files(source)
    if entrypoint not in files:
        raise ArenaError(f"Entrypoint must name a .leek file within the submission: {entrypoint}")
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    return {"entrypoint": entrypoint, "files": hashes, "sha256": digest(hashes)}


def copy_submission(source: Path, target: Path, expected: dict):
    files = source_files(source)
    actual = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    if actual != expected["files"]:
        raise ArenaError(f"Submission changed since scheduling: {source}")
    target.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)


def integer(value, low: int, high: int, label: str):
    if type(value) is not int or not low <= value <= high:
        raise ArenaError(f"{label} must be an integer in [{low}, {high}]")


def validate_scenario(config: dict):
    if not isinstance(config, dict):
        raise ArenaError("scenario must be an object")
    unknown = set(config) - {"team_size", "max_turns", "entity", "map"}
    if unknown:
        raise ArenaError(f"Unsupported scenario fields: {sorted(unknown)}")
    integer(config.get("team_size"), 1, 8, "team_size")
    integer(config.get("max_turns"), 1, 64, "max_turns")
    entity = config.get("entity", {})
    allowed = {"level", "life", "strength", "agility", "frequency", "tp", "mp", "cores", "ram", "weapons", "chips", "wisdom", "resistance", "science", "magic"}
    if not isinstance(entity, dict) or set(entity) - allowed:
        raise ArenaError("Invalid entity fields")
    for key in ("level", "life", "strength", "tp", "mp", "cores", "ram"):
        if key not in entity:
            raise ArenaError(f"Missing entity.{key}")
    for key, value in entity.items():
        if key in {"weapons", "chips"}:
            if not isinstance(value, list) or len(value) > 32:
                raise ArenaError(f"entity.{key} must be a list of up to 32 IDs")
            for item in value:
                integer(item, 1, 100000, key)
        else:
            low = 1 if key in {"level", "life", "cores", "ram"} else 0
            high = 50 if key == "ram" else 100 if key == "cores" else 100000
            integer(value, low, high, key)
    if config.get("map") is not None:
        m = config["map"]
        if not isinstance(m, dict) or set(m) - {"obstacles", "team1", "team2"}:
            raise ArenaError("Custom maps accept obstacles, team1 and team2 only (fixed 18×18 grid)")
        if not isinstance(m.get("obstacles"), dict):
            raise ArenaError("map.obstacles must be an object mapping cell IDs to true")
        for cell, marker in m["obstacles"].items():
            if not str(cell).isdigit() or not 0 <= int(cell) < 613 or marker is not True:
                raise ArenaError("Use valid cell IDs and true for unit obstacles")
        cells = []
        for team in ("team1", "team2"):
            positions = m.get(team)
            if not isinstance(positions, list) or len(positions) != config["team_size"]:
                raise ArenaError("Custom maps require an explicit cell for every member of both teams")
            for cell in positions:
                integer(cell, 0, 612, "map cell")
                if str(cell) in m["obstacles"] or cell in cells:
                    raise ArenaError("Spawns must be distinct and outside obstacles")
                cells.append(cell)


def make_scenario(config: dict, entries: list[str], seed: int) -> dict:
    validate_scenario(config)
    integer(seed, 1, 2**31 - 1, "seed")
    result = {
        "random_seed": seed, "max_turns": config["max_turns"],
        "farmers": [], "teams": [], "entities": [],
    }
    if config.get("map") is not None:
        result["map"] = config["map"]
    for side in range(2):
        owner = side + 1
        result["farmers"].append({"id": owner, "name": f"Side {owner}", "country": "fr"})
        result["teams"].append({"id": owner, "name": f"Side {owner}"})
        result["entities"].append([
            {**config["entity"], "id": side * config["team_size"] + i + 1,
             "name": f"Side {owner} / {i + 1}", "type": 1, "farmer": owner,
             "team": owner, "ai": entries[side], "ai_version": 4}
            for i in range(config["team_size"])
        ])
    return result


def load_manifest(path: Path) -> dict:
    value = read_json(path)
    if not isinstance(value, dict) or set(value) - {"name", "seeds", "include_mirrors", "scenario", "strategies"}:
        raise ArenaError("Invalid tournament manifest fields")
    seeds = value.get("seeds", [])
    if not seeds or len(seeds) != len(set(seeds)):
        raise ArenaError("Seeds must be nonempty and unique")
    for seed in seeds:
        integer(seed, 1, 2**31 - 1, "seed")
    validate_scenario(value.get("scenario", {}))
    if type(value.get("include_mirrors", False)) is not bool:
        raise ArenaError("include_mirrors must be a boolean")
    strategies = value.get("strategies", [])
    if len(strategies) < 2:
        raise ArenaError("At least two strategies are required")
    ids = set()
    for s in strategies:
        name = s.get("id", "")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", name) or name in ids:
            raise ArenaError(f"Invalid or duplicate strategy ID: {name}")
        ids.add(name)
        s["path"] = str((path.parent / s["path"]).absolute())
        s["submission"] = submission(Path(s["path"]), s.get("entrypoint", "main.leek"))
    return value
