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
        "limit": {"type": "integer", "minimum": 1, "description": "Character count; values above 16000 are capped at 16000."}}
TOOLS = [
    {"name": "list_files", "description": "List your .leek source files.", "input_schema": schema()},
    {"name": "read_file", "description": "Read your own source file, using character offsets (not line numbers). Default 16000 characters, maximum 16000 per call. If truncated=true, follow the returned continuation arguments until next_offset=null to finish reading.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name": "write_file", "description": "Save your own .leek file (128 files, 2 MB total). A successful save returns success=true; created/updated distinguish a new file from overwriting an existing file. This does not compile, validate or submit the strategy.",
     "input_schema": schema({"path": TEXT, "content": TEXT}, ["path", "content"])},
    {"name": "read_docs", "description": "Read the frozen shared documentation. For syntax, start with corpus/language/cheatsheet.md; corpus/language/index.md lists short topic tutorials. Game API signatures are in leekscript-v1/api.md. Paths start at authoring.md, corpus/ or leekscript-v1/. Default 16000 characters, maximum 16000 per call. offset counts characters, not lines. A partial read returns truncated=true and an exact continuation call. To read the complete document, repeat with that continuation until next_offset=null; a returned page is not the whole file.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name":"lookup_api","description":"Search the frozen LeekScript 4 API by exact function/constant name or case-insensitive name fragment. Use queries=[name1,name2,...] for up to 20 searches in ONE tool step; results and continuations are separate for each query. Use mode=index to discover compact lists of names without definitions, optionally filter by kind=functions/constants and a query fragment. Follow next_offset using the exact continuation. Search limit defaults to 20 per query (max 50); index defaults to 500 names (max 500). Offsets count matches, not characters. f[integer] describes arguments, not call syntax: call f(argument). Use getEntity(), not removed getLeek(), for your runtime ID.",
     "input_schema":schema({'query':TEXT,'queries':{'type':'array','items':TEXT,'minItems':1,'maxItems':20},'mode':{'type':'string','enum':['search','index']},'kind':{'type':'string','enum':['all','functions','constants']},'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':500}})},
    {"name": "analyze", "description": "Compile/analyze your saved entrypoint and every configured team entrypoint with the native engine. Returns status and readable diagnostic_messages with severity, file, line and compiler code. Analyze after the final edit; fix all errors and repeat until status=valid before submit. Analysis does not change your files.", "input_schema": schema(ENTRY)},
    {"name": "test", "description": "Run two native-engine preparation fights, one per starting side. Default opponent: passive. To compare two of YOUR scripts, write both files then call test with entrypoint='main.leek' and opponent_entrypoint='sparring.leek'. In participant-team mode the opposing side copies your roster and runs that alternate script on every member; your own team.json is unchanged. No other participant sources or evaluation results are accessible. These fights never count toward competition scores. Read the returned test_id with read_replay, keeping side=0 or 1.",
     "input_schema": schema({**ENTRY, "scenario_id": {"type": "string", "enum": ["training"]},
                             "seed_id": {"type": "string", "enum": ["train-17"]},
                             "opponent_id": {"type": "string", "enum": ["passive", "workspace"]}, "opponent_entrypoint": TEXT})},
    {"name": "read_replay", "description": "Read your preparation test: fight actions/entities, team_metrics, turn_metrics, or debug/error logs. Pages use character offsets, not turns or lines. Default and maximum 16000 characters. truncated=true means this is NOT the complete replay: repeat the exact returned continuation (same test_id, side and section) until next_offset=null. A JSON fragment may be incomplete until all pages are read.",
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
    {"name": "list_past_fights", "description": "Feedback branches only: list your own tournament fights from a selected earlier round of this track. Omit round for the previous round; available_rounds lists accessible rounds. Includes results, metrics and the own submitted source round. Paginated by fight count; use next_offset until null. Cannot access other participants or future/reference fights.",
     "input_schema": schema({"round": {"type": "integer", "minimum": 1}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}})},
    {"name": "read_past_fight", "description": "Feedback branches only: inspect an opaque fight_id from list_past_fights. The response identifies the executed own submission by round and provides a read_submitted_file call. overview explains fields; actions provides chronological events and entity IDs; turns provides your per-leek metrics; logs provides only your debug/error output. Text pages use character offsets; follow next_offset. Opponent code and debug output are never available.",
     "input_schema": schema({"fight_id": TEXT, "section": {"type": "string", "enum": ["overview", "actions", "turns", "logs"]}, **PAGE}, ["fight_id"])},
])

TOOLS.extend([
    {'name':'list_submissions','description':'List your own frozen source versions by strategy round (Round 1 is the initial version). Same track and replicate only; no fight results or opponent code. Available with or without feedback. Follow next_offset for more versions.',
     'input_schema':schema({'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':100}})},
    {'name':'read_submitted_file','description':'Read one file of your own earlier submitted strategy. Choose round and path from list_submissions. Character pages: follow continuation until next_offset=null. Cannot access other tracks, opponents, future rounds or match results.',
     'input_schema':schema({'round':{'type':'integer','minimum':1},'path':TEXT,**PAGE},['round','path'])},
])
