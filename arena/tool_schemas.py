"""One tool contract for native APIs and MCP."""
def schema(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [],
            "additionalProperties": False}


TEXT = {"type": "string"}
ENTRY = {"entrypoint": TEXT}
from .stats import STATS
STAT_VALUES = schema({key: {"type": "integer", "minimum": 0, "maximum": 100000} for key in STATS})
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
    {"name": "configure_team", "description": "Choose team members, per-member .leek entrypoints, weapons and chips. Available only when scenario.team_selection enables participant teams. Sources must exist first. Read leekscript-v1/weapons.json and chips.json; weapons use their item field as runtime IDs, chips use their object keys/id. Replay actions use template IDs. Optional per-member capital in realistic-v1 mode or raw stats in free mode; omit to inherit the corresponding default member. Read corpus/stat-rules.json. Realistic builds exclude components; equipment must meet allowlists and slot limits; realistic mode also enforces the leek level (explicit free mode permits higher-level items). The selection is journaled as team.json and frozen with submit.",
     "input_schema": schema({"members": {"type": "array", "minItems": 1, "maxItems": 8,
         "items": schema({"entrypoint": TEXT, "weapons": {"type": "array", "items": {"type": "integer"}},
                          "chips": {"type": "array", "items": {"type": "integer"}}, "capital": STAT_VALUES, "stats": STAT_VALUES}, ["entrypoint", "weapons", "chips"])}}, ["members"])},
    {"name": "submit", "description": "Fige ta soumission et clôt la session.", "input_schema": schema(ENTRY)},
]
