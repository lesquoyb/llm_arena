"""Combat statistics from recorded actions and optional adapter telemetry.

Older outcomes lack per-turn operations and damage source attribution. Keep
those values unknown rather than spreading totals or guessing from turn order.
"""
from collections import defaultdict

COUNTERS = ("actions", "moves", "cells_moved", "shots", "chips", "weapon_changes", "tp_lost", "mp_lost",
            "damage_taken", "damage_dealt", "erosion_taken", "erosion_dealt", "healing_given", "healing_received",
            "deaths", "operations", "ai_turns", "errors", "operation_limit_hits", "stack_overflows")


def combat_stats(outcome, scenario=None):
    limits = {min(2**31-1, e["cores"] * 1_000_000)
              for team in (scenario or {}).get("entities", []) for e in team if type(e.get("cores")) is int}
    limit = next(iter(limits)) if len(limits) == 1 else None
    source = "scenario entity.cores" if limits else "unavailable"
    if not limits and outcome.get("operations_limit_basis") == "entity.cores":
        limit = outcome.get("operations_limit_per_turn")
        source = "recorded entity.cores"

    fight = outcome.get("fight") or {}
    entities = {e["id"]: e for e in fight.get("leeks", [])}
    instrumented = "turn_metrics" in outcome
    def fresh():
        row = dict.fromkeys(COUNTERS, 0)
        if not instrumented:
            row.update(operations=None, damage_dealt=None, erosion_dealt=None, healing_given=None, errors=None, operation_limit_hits=None, stack_overflows=None)
        return row
    rows = defaultdict(fresh)
    turn, actor = 1, None
    def add(entity, key, amount=1):
        if entity in entities:
            rows[(turn, entity)][key] += amount
    for action in fight.get("actions", []):
        if not isinstance(action, list) or not action:
            continue
        code = action[0]
        if code == 6:
            turn, actor = action[1], None
        elif code == 7:
            actor = action[1]
            add(actor, "ai_turns")
        elif code == 8:
            actor = None
        elif code == 10:
            add(action[1], "moves"); add(action[1], "actions")
            add(action[1], "cells_moved", len(action[3]) if len(action) > 3 else 1)
        elif code in (12, 13, 16):
            add(actor, "actions"); add(actor, {12: "chips", 13: "weapon_changes", 16: "shots"}[code])
        elif code in (100, 102):
            add(action[1], "tp_lost" if code == 100 else "mp_lost", action[2])
        elif code in (101, 108, 109, 110, 111):
            add(action[1], "damage_taken", action[2])
            if len(action) > 3:
                add(action[1], "erosion_taken", action[3])
        elif code == 107:
            add(action[1], "erosion_taken", action[2])
        elif code == 103:
            add(action[1], "healing_received", action[2])
        elif code == 5:
            add(action[1], "deaths")
    for measured in outcome.get("turn_metrics", []):
        row = rows[(measured["turn"], measured["entity"])]
        for key in ("operations", "ai_turns", "damage_dealt", "damage_taken", "erosion_dealt", "erosion_taken", "healing_given", "healing_received", "errors", "operation_limit_hits", "stack_overflows"):
            row[key] = measured.get(key)
    turns = [{"turn": t, "entity": entity, "side": entities.get(entity, {}).get("team", 1)-1,
              "name": entities.get(entity, {}).get("name", str(entity)), **data}
             for (t, entity), data in sorted(rows.items())]
    scenario_members = {(e.get("team"), e.get("name")): e
                        for team in (scenario or {}).get("entities", []) for e in team}
    for row in turns:
        member = scenario_members.get((row["side"] + 1, row["name"]), {})
        row["operations_limit_per_turn"] = min(2**31-1, member["cores"] * 1_000_000) if type(member.get("cores")) is int else limit
    totals = []
    for entity, info in entities.items():
        records = [r for r in turns if r["entity"] == entity]
        total = {"entity": entity, "name": info.get("name", str(entity)), "side": info.get("team", 1)-1}
        member = scenario_members.get((info.get("team"), info.get("name")), {})
        total["operations_limit_per_turn"] = min(2**31-1, member["cores"] * 1_000_000) if type(member.get("cores")) is int else limit
        for key in COUNTERS:
            total[key] = None if any(r[key] is None for r in records) else sum(r[key] for r in records)
        if not instrumented:
            total["operations"] = (fight.get("ops") or {}).get(str(entity))
            total.update(damage_dealt=None, erosion_dealt=None, healing_given=None)
        total["operations_per_turn"] = (total["operations"] / total["ai_turns"]
                                        if total["operations"] is not None and total["ai_turns"] else None)
        totals.append(total)
    def combine(records, name, **identity):
        result = {"name": name, **identity}
        for key in COUNTERS:
            result[key] = None if any(r[key] is None for r in records) else sum(r[key] for r in records)
        return result
    sides = [combine([r for r in totals if r["side"] == side], f"Team {side+1}") for side in (0,1)]
    # Older outcomes still have authoritative team-level operation/error totals.
    if not instrumented:
        for side, row in enumerate(sides):
            measured = (outcome.get("team_metrics") or {}).get(str(side), {})
            for key in ("operations", "errors", "operation_limit_hits", "stack_overflows"):
                if key in measured:
                    row[key] = measured[key]
    total = combine(sides, "Match total")
    rounds = [combine([r for r in turns if r["turn"] == turn], "All entities", turn=turn)
              for turn in sorted({r["turn"] for r in turns})]
    return {"total": total, "sides": sides, "rounds": rounds, "entities": totals, "turns": turns, "instrumented": instrumented,
            "operations_limit_per_turn": limit, "operation_limits": sorted(limits),
            "limit_source": source,
            "action_definition": "Moves, weapon changes, shots and chips. Effects are not counted as decisions.",
            "missing": [] if instrumented else ["This archive has no per-turn operations, per-leek errors or damage/healing attribution. Received damage comes from replay events and may include overkill."]}


def competition_stats(matches, load, load_scenario=lambda _: None):
    groups = {}
    for match in matches:
        stage = match["stage"]
        group = groups.setdefault(stage, {"stage": stage, "matrix": {}, "strategies": {}, "matches": 0, "with_replay": 0, "operation_limits": []})
        group["matches"] += 1
        result = match["result"]
        if not match.get("mirror"):
            for side, who in enumerate(match["sides"]):
                opponent = match["sides"][1-side]
                row = group["matrix"].setdefault(who, {}).setdefault(opponent, dict(wins=0, draws=0, losses=0, failures=0))
                key = "failures" if result.get("status") != "completed" else "draws" if result.get("winner_side") == -1 else "wins" if result.get("winner_side") == side else "losses"
                row[key] += 1
        outcome = load(match["path"])
        if not outcome or not outcome.get("fight"):
            continue
        group["with_replay"] += 1
        stats = combat_stats(outcome, load_scenario(match["path"]))
        for cap in stats["operation_limits"] or [stats["operations_limit_per_turn"]]:
            if cap is not None and cap not in group["operation_limits"]:
                group["operation_limits"].append(cap)
        for side, totals in enumerate(stats["sides"]):
            who = match["sides"][side]
            entities = [e for e in stats["entities"] if e["side"] == side]
            row = group["strategies"].setdefault(who, {"id": who, "entity_appearances": 0, "missing_per_turn": 0,
                                                        **dict.fromkeys(COUNTERS, 0)})
            row["entity_appearances"] += len(entities)
            row["missing_per_turn"] += int(not stats["instrumented"])
            for key in COUNTERS:
                value = totals[key]
                row[key] = None if value is None or row[key] is None else row[key] + value
    limits = sorted({cap for g in groups.values() for cap in g["operation_limits"]})
    return {"stages": list(groups.values()), "operation_limits": limits,
            "operations_limit_per_turn": limits[0] if len(limits) == 1 else None}
