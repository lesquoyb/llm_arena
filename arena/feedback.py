"""Read-only capability for a feedback branch's own frozen Round 1 fights."""
import json
from .core import ArenaError, digest, read_json

FEEDBACK_NAMES = {'list_past_fights', 'read_past_fight'}
METRICS = ('operations', 'errors', 'operation_limit_hits', 'stack_overflows', 'turns',
           'damage_dealt', 'damage_taken', 'healing_given', 'healing_received', 'ai_turns')
ACTION_GUIDE = {0: 'Fight started', 4: 'Fight ended', 5: 'Death: entity, killer',
    6: 'New turn: turn number', 7: 'Entity turn started: entity', 8: 'Entity turn ended: entity',
    9: 'Summon: caster, summoned entity, target cell, result',
    10: 'Movement: entity, destination cell, path', 12: 'Chip use: chip template, target cell, result',
    13: 'Equip weapon: weapon template', 16: 'Weapon shot: target cell, result',
    100: 'AP removed: entity, amount', 101: 'Damage: target entity, HP lost, maximum HP lost',
    102: 'MP removed: entity, amount', 103: 'Healing: target entity, HP restored',
    107: 'Erosion: target entity, maximum HP lost', 110: 'Poison damage: target entity, HP lost'}


def allowed(state):
    return state.get('generation', 0) > 0 and state.get('condition') == 'feedback' and bool(state.get('parent'))


def access_for(out, state):
    if state.get("calibration"):
        from .calibration import CalibrationFights
        return CalibrationFights(out, state)
    return PastFights(out, state['parent']) if allowed(state) else None


def available_tools(state):
    from .tool_schemas import TOOLS
    if state.get("calibration"):
        names = state["calibration"]["tools"]
        descriptions = {
            'list_past_fights':'List your completed previous-round calibration training and previous-version fights; every response identifies the round. Paginate with offset/limit and next_offset. Validation and audit fights, other training rounds, replicates and prompt candidates are inaccessible.',
            'read_past_fight':'Inspect a fight_id from list_past_fights: overview explains results and metrics; actions gives ordered events; turns gives per-entity metrics; logs gives your side only. Character pages use offset/limit and next_offset. Validation and audit records cannot be read.'}
        return [{**tool, 'description':descriptions.get(tool['name'],tool['description'])}
                for tool in TOOLS if tool['name'] in names]
    return [{**tool, 'description':tool['description'].replace('Round 1', f"Round {state.get('generation', 0)}")}
            if tool['name'] in FEEDBACK_NAMES and state.get('generation',0)>1 else tool
            for tool in TOOLS if tool['name'] not in FEEDBACK_NAMES or allowed(state)]


class PastFights:
    def __init__(self, out, parent):
        import re
        previous = re.search(r'-g(\d+)-(?:control|feedback)$', parent)
        self.root, self.parent = out / (f'g{previous[1]}-tournament' if previous else 'tournament'), parent
        self.round = int(previous[1])+1 if previous else 1

    def records(self):
        result = {}
        for path in sorted((self.root / 'records').glob('*.json')):
            record = read_json(path)
            match = record['match']
            if match.get('mirror') or self.parent not in match['sides']:
                continue
            result['fight-' + digest({'parent': self.parent, 'record': path.name})[:20]] = record
        return result

    def overview(self, identifier, record):
        match, result = record['match'], record['result']
        side = match['sides'].index(self.parent)
        return {'fight_id': identifier, 'round':match.get('round',self.round), 'opponent': 'opponent-' + digest(match['sides'][1-side])[:8],
                'own_side': side, 'status': result['status'],
                'result': ('unscored' if result['status'] != 'completed' else 'draw' if result['winner_side'] == -1
                           else 'win' if result['winner_side'] == side else 'loss'),
                'turns': result.get('turns'),
                'own_metrics': {k: v for k, v in result.get('team_metrics', {}).get(str(side), {}).items() if k in METRICS}}

    def summary(self):
        matches = [self.overview(key, row) for key, row in self.records().items()]
        counts = {key: sum(row['result'] == key for row in matches) for key in ('win', 'draw', 'loss', 'unscored')}
        return {'matches': len(matches), 'wins': counts['win'], 'draws': counts['draw'],
                'losses': counts['loss'], 'failures': counts['unscored']}

    def call(self, name, arguments):
        fields = {'offset', 'limit'} if name == 'list_past_fights' else {'fight_id', 'section', 'offset', 'limit'}
        if set(arguments) - fields:
            raise ArenaError('Unknown feedback tool arguments')
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 20 if name == 'list_past_fights' else 4000)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= (100 if name == 'list_past_fights' else 16000):
            raise ArenaError('Invalid feedback page')
        records = self.records()
        if name == 'list_past_fights':
            matches = [self.overview(key, row) for key, row in records.items()]
            end = min(len(matches), offset+limit)
            return {'round':self.round, 'scope': 'Your previous-round tournament fights; mirrors excluded. Results are from your perspective.',
                    'total': len(matches), 'matches': matches[offset:end],
                    'next_offset': end if end < len(matches) else None}
        record = records.get(arguments.get('fight_id'))
        if record is None:
            raise ArenaError('Fight is not available to this feedback branch')
        section = arguments.get('section', 'overview')
        if section not in {'overview', 'actions', 'turns', 'logs'}:
            raise ArenaError('Unknown fight section')
        view = self.overview(arguments['fight_id'], record)
        if section == 'overview':
            content = {**view, 'guide': 'own_side is 0 or 1; runtime entity IDs are listed in actions. HP=health, AP=action points, MP=movement points. operations counts LeekScript work, errors counts script errors. Top-level turns is fight length; own_metrics.turns sums executed entity turns. operation_limit_hits counts script turns that hit their operation cap. Missing metrics are unknown.',
                       'sections': {'actions': 'Ordered combat events with an action argument guide and initial entities.',
                                    'turns': 'Your per-turn and per-leek numeric metrics.',
                                    'logs': 'Only your side debug/error logs; never opposing scripts or logs.'}}
        else:
            from .preparation import local_path
            replay_path = local_path(self.root, record['directory']) / 'outcome.json'
            if not replay_path.is_file():
                raise ArenaError('No replay was recorded for this fight; read overview for its status')
            outcome = read_json(replay_path)
            if not isinstance(outcome, dict):
                raise ArenaError('No replay was recorded for this fight; read overview for its status')
            side = view['own_side']
            if section == 'logs':
                content = {'own_side': side, 'logs': outcome.get('logs', {}).get(str(side+1), {}),
                           'guide': 'Only your farmer debug/error output. Object keys are public action indices in the fight, not entity IDs or turn numbers. Values are arrays of log entries. Each entry starts [entity_id, log_type]. Types 1/2/3 are debug/warning/error messages: [entity_id, log_type, message, optional_color, optional_file, optional_line]. Types 6/7/8 are system info/warning/error: [entity_id, log_type, trace, error_code, optional_parameters]. Other types are visual/debug controls. Opponent debug output is excluded.'}
            elif section == 'turns':
                content = {'own_side': side, 'metrics': [{k:v for k,v in row.items() if k in (*METRICS, 'turn', 'entity', 'side')}
                           for row in sorted(outcome.get('turn_metrics', []), key=lambda row: (row.get('turn', 0), row.get('entity', 0))) if row.get('side') == side],
                           'guide': 'Each record describes one entity on one turn. damage_taken/dealt and healing are HP; operations is computation, not LLM tokens.'}
            else:
                fight = outcome.get('fight', {})
                events, turn, actor = [], 1, None
                def numeric(value):
                    return type(value) in (int, float, bool) or value is None or isinstance(value, list) and all(numeric(v) for v in value)
                for action in fight.get('actions', []):
                    if not isinstance(action, list) or not action or not all(numeric(v) for v in action) or action[0] in {203, 205}:
                        continue
                    if action[0] == 6 and len(action)>1: turn = action[1]
                    if action[0] == 7 and len(action)>1: actor = action[1]
                    events.append({'turn': turn, 'actor': actor, 'action': ACTION_GUIDE.get(action[0], 'Other public engine action'), 'code': action[0], 'arguments': action[1:]})
                content = {'own_side': side, 'guide': 'Events are chronological. actor is the active entity; team is 1 for side 0, 2 for side 1. Chip/weapon IDs here are replay templates, not runtime item IDs. String debug/chat payloads are excluded.',
                           'entities': [{k:v for k,v in leek.items() if k in {'id','team','life','cellPos','summon','level','strength','tp','mp'}} for leek in fight.get('leeks', [])], 'events': events}
        from .model_content import compact, page
        return {**page(compact(content),arguments,name,{'fight_id':arguments['fight_id'],'section':section},default=4000),
                'round':self.round}
