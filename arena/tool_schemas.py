"""One tool contract for native APIs and MCP."""
def schema(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [],
            "additionalProperties": False}


TEXT = {"type": "string"}
ENTRY = {"entrypoint": TEXT}
from .stats import STATS
STAT_VALUES = schema({key: {"type": "integer", "minimum": 0, "maximum": 100000} for key in STATS})
FINAL_STATS = schema({key: {"type": "integer", "minimum": -100000 if key in ("strength", "agility", "wisdom", "resistance", "science", "magic", "frequency") else 0, "maximum": 100000} for key in STATS})
LEVEL = {'type': 'integer', 'minimum': 1, 'maximum': 301}
COMPONENTS = {'type': 'array', 'maxItems': 8, 'items': {'anyOf': [
    {'type': 'integer'}, schema({'template': {'type': 'integer'},
        'stats': schema({key: {'type': 'integer', 'minimum': -100000, 'maximum': 100000}
                         for key in STATS})}, ['template'])]}}
PAGE = {"offset": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer", "minimum": 1, "maximum": 16000}}
TOOLS = [
    {"name": "list_files", "description": "List your .leek source files.", "input_schema": schema()},
    {"name": "read_file", "description": "Read your own source file, using character offsets (not line numbers). Default 16000 characters, maximum 16000 per call. If truncated=true, follow the returned continuation arguments until next_offset=null to finish reading.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name": "write_file", "description": "Write your own .leek file (128 files, 2 MB total).",
     "input_schema": schema({"path": TEXT, "content": TEXT}, ["path", "content"])},
    {"name": "read_docs", "description": "Read the pinned shared documentation. Paths start at authoring.md, corpus/ or leekscript-v1/. Default 16000 characters, maximum 16000 per call. offset counts characters, not lines. A partial read returns truncated=true and an exact continuation call. To read the complete document, repeat with that continuation until next_offset=null; a returned page is not the whole file.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name": "analyze", "description": "Compile/analyze your saved entrypoint and every configured team entrypoint with the native engine. Returns status and readable diagnostic_messages with severity, file, line and compiler code. Analyze after the final edit; fix all errors and repeat until status=valid before submit. Analysis does not change your files.", "input_schema": schema(ENTRY)},
    {"name": "test", "description": "Run two native-engine training fights against passive, one per starting side. Read the returned test ID with read_replay for actions, metrics and debug/errors.",
     "input_schema": schema({**ENTRY, "scenario_id": {"type": "string", "enum": ["training"]},
                             "seed_id": {"type": "string", "enum": ["train-17"]},
                             "opponent_id": {"type": "string", "enum": ["passive"]}})},
    {"name": "read_replay", "description": "Read a page of your own preparation test: fight actions/entities, team_metrics, turn_metrics, or debug/error logs.",
     "input_schema": schema({"test_id": TEXT, "side": {"type": "integer", "enum": [0, 1]},
                             "section": {"type": "string", "enum": ["fight", "team_metrics", "turn_metrics", "logs"]}, **PAGE}, ["test_id"])},
    {"name": "configure_team", "description": "Choose team members, per-member .leek entrypoints, weapons and chips. Available only when scenario.team_selection enables participant teams. Sources must exist first. Boss/internal and summon-only chips are forbidden in all modes. Read leekscript-v1/weapons.json and chips.json; weapons use their item field as runtime IDs, chips use their object keys/id. Replay actions use template IDs. With independent_builds, choose an explicit level (1–301) and capital for every member; components default to none and reference stats are not imposed. Per-member capital is required when scenario.team_selection.require_capital is true, otherwise optional in realistic-v1 mode or raw stats in free mode; omit to inherit the corresponding default member. Read corpus/stat-rules.json. Realistic builds accept component item-template IDs or {template, stats} altered instances. Use corpus/component-rules.json for current stats, levels and capacities; it overrides the older generator component catalog. Duplicates and over-level pieces are rejected; eight slots are enforced (recovery components consume three), and alteration charge cannot exceed capacity; equipment must meet allowlists and slot limits; realistic mode also enforces the leek level, RAM chip capacity, level-based weapon capacity and special-item restrictions (explicit free mode permits higher-level items). The selection is journaled as team.json and frozen with submit.",
     "input_schema": schema({"members": {"type": "array", "minItems": 1, "maxItems": 8,
         "items": schema({"entrypoint": TEXT, "level": LEVEL, "name": {"type": "string", "minLength": 1, "maxLength": 80}, "weapons": {"type": "array", "items": {"type": "integer"}},
                          "chips": {"type": "array", "items": {"type": "integer"}}, "capital": STAT_VALUES, "stats": FINAL_STATS, "components": COMPONENTS}, ["entrypoint", "weapons", "chips"])}}, ["members"])},
    {"name": "submit", "description": "Freeze your saved sources and configured team, then end preparation. This does not check compilation or repair code. First call analyze on the final saved version and fix errors until status=valid. After submit you cannot repair this version during its evaluation fights.", "input_schema": schema(ENTRY)},
]

# Identical contracts across native provider APIs and MCP.
team_schema = next(t['input_schema'] for t in TOOLS if t['name'] == 'configure_team')
TOOLS.extend([
    {'name': 'preview_build', 'description': 'Read-only realistic build calculator. Supply capital amounts, not final stats. Returns final stats, remaining capital, component bonuses/slots, weapon/chip slots and the next tier costs at the supplied level (1–301); independent builds default the calculator to level 301, otherwise it uses the reference member level. No files or team.json are changed.',
     'input_schema': schema({'components': COMPONENTS, 'level': LEVEL, 'capital': STAT_VALUES, 'member_index': {'type': 'integer', 'minimum': 0, 'maximum': 7}}, ['capital'])},
    {'name': 'validate_team', 'description': 'Read-only team validation before configure_team. Checks team size, level, capital, player item IDs, equipment level, RAM/chip slots, weapon slots, component levels, slots and alteration capacity and competition limits. Sources need not exist yet: missing entrypoints are reported separately. Returns valid=false and errors for invalid builds. Does not write team.json or submit.',
     'input_schema': team_schema},
])

TOOLS.extend([
    {"name": "list_past_fights", "description": "Feedback branches only: list your frozen Round 1 tournament fights with readable win/draw/loss results and your metrics. Paginated by fight count; use next_offset until null. Cannot access other participants or future/reference fights.",
     "input_schema": schema({"offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}})},
    {"name": "read_past_fight", "description": "Feedback branches only: inspect an opaque fight_id from list_past_fights. overview explains fields; actions provides chronological events and entity IDs; turns provides your per-leek metrics; logs provides only your debug/error output. Text pages use character offsets; follow next_offset. Opponent code and debug output are never available.",
     "input_schema": schema({"fight_id": TEXT, "section": {"type": "string", "enum": ["overview", "actions", "turns", "logs"]}, **PAGE}, ["fight_id"])},
])
