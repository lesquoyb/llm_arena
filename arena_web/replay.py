"""Labels and coordinates for the pinned engine's public action format."""
from __future__ import annotations

LABELS = {0: "Fight started", 4: "Fight ended", 5: "Death", 6: "New turn",
          7: "Entity turn started", 8: "Entity turn ended", 9: "Summon",
          10: "Movement", 11: "Direct kill", 12: "Chip use",
          13: "Weapon change", 14: "Stacked effect", 15: "Chest opened", 16: "Shot",
          17: "Awakening", 18: "Sleep", 100: "AP removed", 101: "Damage", 102: "MP removed",
          103: "Healing", 104: "Vitality", 105: "Resurrection", 106: "Strength loss",
          107: "Erosion", 108: "Reflected damage", 109: "Life damage",
          110: "Poison", 111: "Aftereffect", 112: "Nova vitality", 201: "Lama", 203: "Message",
          205: "Cell highlighted", 301: "Weapon effect", 302: "Chip effect", 303: "Effect ended",
          304: "Effect updated", 306: "Effects reduced", 307: "Poisons removed",
          308: "Shackles removed", 309: "Effect duration changed", 1000: "Engine error",
          1001: "Map changed", 1002: "Strategy error"}


def cell_position(identifier, width=18):
    # Same integer formula as maps/Cell.java in engine.lock.json's commit.
    remainder = identifier % (2 * width - 1)
    y = identifier // (2 * width - 1) - remainder % width
    x = (identifier - (width - 1) * y) // width
    return {"id": identifier, "x": (x - y) * 12, "y": (x + y) * 6}


def describe(fight):
    width, height = fight.get("map", {}).get("width", 18), fight.get("map", {}).get("height", 18)
    names = {leek["id"]: leek.get("name", str(leek["id"])) for leek in fight.get("leeks", [])}
    turn, actor, events, unknown = 1, None, [], set()
    for index, action in enumerate(fight.get("actions", [])):
        if not isinstance(action, list) or not action:
            continue
        code = action[0]
        label = LABELS.get(code, f"Action {code}")
        if code not in LABELS or code == 1001:
            unknown.add(code)
        if code == 6 and len(action) > 1:
            turn = action[1]
            label = f"Turn {turn}"
        elif code == 7 and len(action) > 1:
            actor = action[1]
            label = f"{names.get(actor, actor)} starts its turn"
        elif code == 10 and len(action) > 2:
            label = f"{names.get(action[1], action[1])} moves to cell {action[2]}"
        elif code in {101, 108, 109, 110, 111} and len(action) > 2:
            label = f"{names.get(action[1], action[1])} loses {action[2]} HP ({LABELS.get(code)})"
        elif code == 107 and len(action) > 2:
            label = f"{names.get(action[1], action[1])} loses {action[2]} maximum HP (erosion)"
        elif code == 103 and len(action) > 2:
            label = f"{names.get(action[1], action[1])} recovers {action[2]} HP"
        elif code == 5 and len(action) > 1:
            label = f"{names.get(action[1], action[1])} dies"
        elif code == 16 and len(action) > 2:
            label = f"{names.get(actor, actor)} shoots at cell {action[1]} (result {action[2]})"
        elif code == 12 and len(action) > 3:
            label = f"{names.get(actor, actor)} uses chip {action[1]} on cell {action[2]}"
        elif code == 13 and len(action) > 1:
            label = f"{names.get(actor, actor)} equips weapon {action[1]}"
        events.append({"index": index, "turn": turn, "actor": actor, "code": code, "text": label, "raw": action})
    return {"cells": [cell_position(i, width) for i in range((2 * width - 1) * height - (width - 1))],
            "events": events, "unknown_codes": sorted(unknown),
            "note": "Schematic replay: positions, HP, shots, healing and deaths. "
                    "Some effects and official client animations are not reproduced. "
                    "Raw events are the reference."}
