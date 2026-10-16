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
    {"name": "list_files", "description": "Liste tes fichiers .leek.", "input_schema": schema()},
    {"name": "read_file", "description": "Lit une page de ton fichier.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name": "write_file", "description": "Écrit ton fichier .leek (128 fichiers, 2 Mo au total).",
     "input_schema": schema({"path": TEXT, "content": TEXT}, ["path", "content"])},
    {"name": "read_docs", "description": "Lit une page du corpus commun figé.",
     "input_schema": schema({"path": TEXT, **PAGE}, ["path"])},
    {"name": "analyze", "description": "Analyse le point d'entrée et renvoie ses diagnostics.", "input_schema": schema(ENTRY)},
    {"name": "test", "description": "Test de préparation contre passive, seed train-17, deux positions.",
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
    {"name": "submit", "description": "Fige ta soumission et clôt la session.", "input_schema": schema(ENTRY)},
]

# Identical contracts across native provider APIs and MCP.
team_schema = next(t['input_schema'] for t in TOOLS if t['name'] == 'configure_team')
TOOLS.extend([
    {'name': 'preview_build', 'description': 'Read-only realistic build calculator. Supply capital amounts, not final stats. Returns final stats, remaining capital, component bonuses/slots, weapon/chip slots and the next tier costs at the supplied level (1–301); independent builds default the calculator to level 301, otherwise it uses the reference member level. No files or team.json are changed.',
     'input_schema': schema({'components': COMPONENTS, 'level': LEVEL, 'capital': STAT_VALUES, 'member_index': {'type': 'integer', 'minimum': 0, 'maximum': 7}}, ['capital'])},
    {'name': 'validate_team', 'description': 'Read-only team validation before configure_team. Checks team size, level, capital, player item IDs, equipment level, RAM/chip slots, weapon slots, component levels, slots and alteration capacity and competition limits. Sources need not exist yet: missing entrypoints are reported separately. Returns valid=false and errors for invalid builds. Does not write team.json or submit.',
     'input_schema': team_schema},
])
