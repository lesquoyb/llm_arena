"""Read public LeekWars teams only; never infer private or missing builds."""
from datetime import datetime, timezone
import json
from urllib.request import Request, urlopen
from urllib.error import URLError

from .core import ArenaError, ROOT, digest, validate_scenario
from .equipment import catalog
from .stats import STATS

BASE = 'https://leekwars.com/api/'
RANKING = 'ranking/get-active/team/talent/1/null'


def public_json(path):
    request = Request(BASE + path, headers={'Accept': 'application/json', 'User-Agent': 'LLMArena/1 public-team-import'})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ArenaError('Public response exceeds 4 MB')
        data = json.loads(raw)
    except (URLError, ValueError, OSError) as error:
        raise ArenaError(f'Cannot read public LeekWars endpoint {BASE + path}: {error}') from error
    if not isinstance(data, dict):
        raise ArenaError('Unexpected public LeekWars response')
    if data.get('success') is False:
        raise ArenaError('Public LeekWars request was rejected')
    return data


# Selection supplied by the user from the current top farmer's public page.
DREAM_FARMER_ID = 512
DREAM_LEEK_IDS = (599, 881, 1549, 11942)


def fetch_snapshot(fetch=public_json):
    farmer = fetch('farmer/get/' + str(DREAM_FARMER_ID))
    if farmer.get('id') != DREAM_FARMER_ID:
        raise ArenaError('Public farmer response does not match farmer 512')
    leeks = [fetch('leek/get/' + str(identifier)) for identifier in DREAM_LEEK_IDS]
    if any(leek.get('id') != identifier for leek, identifier in zip(leeks, DREAM_LEEK_IDS)):
        raise ArenaError('Public leek response does not match the selected leek ID')
    return {'fetched_at': datetime.now(timezone.utc).isoformat(),
            'selection': {'farmer_id': DREAM_FARMER_ID, 'leek_ids': list(DREAM_LEEK_IDS),
                          'source': 'User-selected public top farmer; not a team-composition ranking'},
            'farmer': farmer, 'leeks': leeks}


def scenario_from_snapshot(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('leeks'), list) or len(snapshot['leeks']) != 4:
        raise ArenaError('Import requires a public snapshot with exactly four leek records')
    members = []
    catalogs = {kind: catalog(ROOT / 'docs/leekscript-v1', kind) for kind in ('weapons', 'chips')}
    for leek in snapshot['leeks']:
        stats = {}
        for stat in STATS:
            value = leek.get('total_' + stat)
            if type(value) is not int:
                raise ArenaError(f'Public leek {leek.get("id")} is missing total_{stat}; its build cannot be reproduced')
            stats[stat] = value
        member = {'name': str(leek['name']), 'level': leek['level'], 'stats': stats}
        for kind in ('weapons', 'chips'):
            if not isinstance(leek.get(kind), list):
                raise ArenaError(f'Public leek {leek.get("id")} has no public {kind} list')
            ids = [item.get('template') if isinstance(item, dict) else item for item in leek[kind]]
            if any(type(i) is not int or str(i) not in catalogs[kind] for i in ids):
                raise ArenaError(f'Public leek {leek.get("id")} uses unsupported or non-player {kind}; import aborted')
            member[kind] = ids
        members.append(member)
    first = members[0]
    # Published totals include components: preserve totals, never pretend they are
    # achievable with the capital-only realistic-v1 builder or apply bonuses twice.
    scenario = {'preset': 'dream-team', 'team_size': 4, 'max_turns': 1000,
                'stats_mode': 'free', 'entity': {'level': first['level'], **first['stats'],
                    'weapons': first['weapons'], 'chips': first['chips']}, 'member_stats': members,
                'source': {'kind': 'leekwars-public-team', 'imported_at': datetime.now(timezone.utc).isoformat(),
                    'snapshot_sha256': digest(snapshot), 'snapshot': snapshot}}
    validate_scenario(scenario)
    return scenario
