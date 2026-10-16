"""Freeze public component stats, levels, capacities and alteration parameters together."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://leekwars.com/api/data/get-all'
CLIENT_COMMIT = '2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9'


def extract(payload):
    data = payload['data']
    alterations = data['alterations']
    if set(alterations['weights']) != {'life', 'strength', 'agility', 'wisdom',
            'resistance', 'science', 'magic', 'frequency', 'tp', 'mp', 'cores', 'ram'}:
        raise ValueError('Unexpected alteration characteristics')
    components = {}
    for row in data['components'].values():
        template = row['template']
        level = data['items'][str(template)]['level']
        if type(level) is not int or not 1 <= level <= 301:
            raise ValueError(f'Invalid component level: {template}')
        if type(row['capacity']) is not int or row['capacity'] < 0:
            raise ValueError(f'Invalid alteration capacity: {template}')
        if (not isinstance(row['stats'], list) or any(k not in alterations['weights']
                or type(v) is not int for k, v in row['stats'])):
            raise ValueError(f'Invalid component stats: {template}')
        components[str(template)] = {**row, 'level': level,
                                    'slots': 3 if template in (406, 407) else 1}
    return {'schema_version': 1, 'source_url': URL,
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'master_version': payload['master_version'],
            'payload_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True,
                separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
            'client_commit': CLIENT_COMMIT,
            'source_url_rules': f'https://github.com/leek-wars/leek-wars/blob/{CLIENT_COMMIT}/src/model/alteration.ts',
            'deficit_refund': 0.25, 'components': components, 'alterations': alterations}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Previously saved data/get-all response')
    parser.add_argument('--out', type=Path, default=ROOT/'docs/corpus/component-rules.json')
    args = parser.parse_args()
    if args.snapshot:
        payload = json.loads(args.snapshot.read_text(encoding='utf-8'))
    else:
        with urlopen(Request(URL, headers={'User-Agent': 'LLMArena/1'}), timeout=30) as response:
            payload = json.load(response)
    result = extract(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + '.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.out)
    print(f'Component and alteration rules saved to {args.out}')
