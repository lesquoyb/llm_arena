"""Fetch a public top-team snapshot for import in the arena UI."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arena.public_teams import fetch_snapshot, scenario_from_snapshot
from arena.core import ArenaError

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('runs/dream-team-public.json'))
    args = parser.parse_args()
    try:
        snapshot = fetch_snapshot()
        scenario_from_snapshot(snapshot)  # Reject incomplete or incompatible data.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Public snapshot saved to {args.out}')
    except ArenaError as error:
        parser.exit(1, str(error) + '\n')
