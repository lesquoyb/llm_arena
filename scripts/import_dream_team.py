"""Fetch four public leeks of the current first-ranked farmer for import in the arena UI."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arena.public_teams import fetch_snapshot, scenario_from_snapshot
from arena.core import ArenaError, ROOT
from arena.presets import save_dream_team

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('runs/dream-team-public.json'))
    parser.add_argument("--save-preset", action="store_true", help="Freeze the validated team in data/presets/dream-team.json")
    parser.add_argument("--snapshot", type=Path, help="Use an already fetched JSON snapshot without network access")
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else fetch_snapshot()
        scenario_from_snapshot(snapshot)  # Reject incomplete or incompatible data.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if args.save_preset:
            save_dream_team(snapshot, ROOT / "data/presets/dream-team.json")
        print(f'Public snapshot saved to {args.out}')
    except (ArenaError, OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')
