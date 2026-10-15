"""Export public component equipment levels missing from the pinned engine data."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://leekwars.com/api/data/get-all'


def extract(data):
    payload = data.get('data', data)
    items = payload.get('items', {})
    if isinstance(items, list):
        items = {str(row['id']): row for row in items}
    pinned = json.loads((ROOT/'docs/leekscript-v1/components.json').read_text(encoding='utf-8'))
    levels = {}
    for component in pinned.values():
        template = component['template']
        item = items.get(str(template), items.get(template))
        if not isinstance(item, dict) or type(item.get('level')) is not int:
            raise ValueError(f'Missing public level for component template {template}')
        levels[str(template)] = item['level']
    return {'source_url': URL, 'fetched_at': datetime.now(timezone.utc).isoformat(),
            'master_version': data.get('master_version'), 'levels': levels}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'docs/corpus/component-levels.json')
    parser.add_argument('--snapshot', type=Path, help='Read a previously exported game-data JSON')
    args = parser.parse_args()
    try:
        if args.snapshot:
            payload = json.loads(args.snapshot.read_text(encoding='utf-8'))
        else:
            request = Request(URL, headers={'Accept':'application/json','User-Agent':'LLMArena/1'})
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
        output = extract(payload)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'Component levels saved to {args.out}')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, str(error)+'\n')
