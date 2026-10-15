"""Portable audited exports; runtime identities retained as provenance."""
import shutil
from pathlib import Path
from .core import ArenaError, file_hash, is_link, read_json, write_json
from .experiment import Journal, experiment_lock


def export_experiment(source: Path, target: Path):
    source, target = source.resolve(), target.resolve()
    if target.exists() or target.is_relative_to(source):
        raise ArenaError("Export target must be a new directory outside the experiment")
    with experiment_lock(source):
        journal = Journal(source)
        try:
            journal.verify()
            target.mkdir(parents=True)
            for path in source.rglob("*"):
                if is_link(path):
                    raise ArenaError("Links are not allowed in exports")
                if not path.is_file() or path.name in {".lock", "journal.sqlite", "journal.sqlite-wal", "journal.sqlite-shm"}:
                    continue
                dest = target / path.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
            # Consistent backup even when WAL is active.
            import sqlite3
            backup = sqlite3.connect(target / "journal.sqlite")
            journal.db.backup(backup)
            backup.close()
            identity = read_json(source / "experiment.json")
            # Portable index, separate from exact runtime checkpoint used for resume.
            manifest = {"schema_version": 1, "config": identity["config"],
                        "files": {p.relative_to(target).as_posix(): file_hash(p)
                                  for p in sorted(target.rglob("*")) if p.is_file()},
                        "note": "Self-contained audit archive; resuming requires the recorded runtime identity."}
            write_json(target / "export.json", manifest)
            return {"exported": str(target), "files": len(manifest["files"])}
        finally:
            journal.db.close()
