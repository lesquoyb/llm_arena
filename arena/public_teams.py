"""Read public LeekWars teams only; never infer private or missing builds."""
from datetime import datetime, timezone
import json
from urllib.request import Request, urlopen
from urllib.error import URLError

from .core import ArenaError, ROOT, digest, validate_scenario
from .equipment import catalog
from .stats import STATS

BASE = 'https://leekwars.com/api/'
RANKING = 'ranking/get-active/farmer/talent/1/null'


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


def fetch_snapshot(fetch=public_json):
    ranking = fetch(RANKING)
    rows = ranking.get('ranking')
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise ArenaError('The public farmer ranking has no first entry')
    leader = rows[0]
    identifier = leader.get('id')
    if type(identifier) is not int or identifier <= 0:
        raise ArenaError('The first public farmer has no valid ID')
    response = fetch('farmer/get/' + str(identifier))
    farmer = response.get('farmer', response)
    if not isinstance(farmer, dict) or farmer.get('id') != identifier:
        raise ArenaError('Public farmer response does not match the current ranking leader')
    records = farmer.get('leeks')
    if isinstance(records, dict):
        records = list(records.values())
    if not isinstance(records, list) or any(not isinstance(l, dict) for l in records):
        raise ArenaError('The first farmer has no public leek list')
    records = [l for l in records if not l.get('deleted')]
    if len(records) < 4:
        raise ArenaError('The first farmer has fewer than four public leeks; no substitute team was generated')
    records = sorted(records, key=lambda l: (-(l.get('talent') or 0), -(l.get('level') or 0), l.get('id', 0)))[:4]
    ids = [l.get('id') for l in records]
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != 4:
        raise ArenaError('The selected public leeks have invalid or duplicate IDs')
    leeks = []
    for leek_id in ids:
        response = fetch('leek/get/' + str(leek_id))
        leek = response.get('leek', response)
        if not isinstance(leek, dict) or leek.get('id') != leek_id:
            raise ArenaError('Public leek response does not match the selected leek ID')
        owner = leek.get('farmer')
        owner_id = owner.get('id') if isinstance(owner, dict) else owner
        if owner_id is not None and owner_id != identifier:
            raise ArenaError('A selected leek changed owner during import; retry the refresh')
        leeks.append(leek)
    return {'fetched_at': datetime.now(timezone.utc).isoformat(), 'ranking_path': RANKING,
            'rank': 1, 'ranking_entry': leader,
            'selection': {'farmer_id': identifier, 'leek_ids': ids,
                          'rule': 'First ranked farmer; four highest-talent public leeks, ties by level then ID'},
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
        if 'components' in leek:
            if (not isinstance(leek['components'], list)
                    or any(isinstance(piece, dict) and 'template' not in piece for piece in leek['components'])):
                raise ArenaError('Public components must be a list')
            member['components'] = [
                ({'template': piece['template'], **({'stats': piece['stats']} if piece.get('stats') else {})}
                 if isinstance(piece, dict) else piece)
                for piece in leek['components'] if piece is not None]
        members.append(member)
    first = members[0]
    # Published totals include components: preserve totals, never pretend they are
    # achievable without validated alteration rules or apply bonuses twice.
    scenario = {'preset': 'dream-team', 'team_size': 4, 'max_turns': 1000,
                'stats_mode': 'free', 'entity': {'level': first['level'], **first['stats'],
                    'weapons': first['weapons'], 'chips': first['chips']}, 'member_stats': members,
                'source': {'kind': 'leekwars-public-team', 'imported_at': datetime.now(timezone.utc).isoformat(),
                    'snapshot_sha256': digest(snapshot), 'snapshot': snapshot}}
    validate_scenario(scenario)
    return scenario
