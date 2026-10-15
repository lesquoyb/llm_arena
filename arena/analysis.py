"""Descriptive reports with paired comparisons and explicit missingness."""
from __future__ import annotations
import csv
import html
import json
import random
from pathlib import Path
from .core import write_json
from .usage import amount


def score(records):
    completed = [r for r in records if r["result"]["status"] == "completed"]
    points = sum(0.5 if r["result"]["winner_side"] == -1 else
                 int(r["result"]["winner_side"] == r["side"]) for r in completed)
    return {"score": points / len(completed) if completed else None,
            "completed": len(completed), "failed": len(records) - len(completed),
            "operations": sum(r["result"]["team_metrics"][str(r["side"])]["operations"] for r in completed),
            "errors": sum(r["result"]["team_metrics"][str(r["side"])]["errors"] for r in completed),
            "operation_limit_hits": sum(r["result"]["team_metrics"][str(r["side"])]["operation_limit_hits"] for r in completed)}


def analyze_evolution(config, out, states, initial, branches, baseline, evolved, contemporaries):
    rows = []
    providers = {model["id"]: model["provider"] for model in config["models"]}
    initial_ids = {participant["id"] for participant in initial}
    for participant in [*initial, *branches]:
        sid = participant["id"]
        generation = 1 if "parent" in participant else 0
        records = evolved.values() if generation else baseline.values()
        records = [r for r in records if r["session"] == sid]
        for panel_name, selected in (("all", records),
                                     ("g0", [r for r in records if r["opponent"] in initial_ids]),
                                     ("controls", [r for r in records if r["opponent"] not in initial_ids])):
            rows.append({"session": sid, "model": participant["model"], "replicate": participant["replicate"],
                         "generation": generation, "condition": participant.get("condition", "initial"),
                         "validity": states[sid].get("validity", "unknown"),
                         "panel": panel_name, **score(selected),
                         "cost_usd": None if states[sid]["status"] == "needs_reconciliation" or
                                            amount(states[sid].get("money_reserved", "0")) > 0
                                     else states[sid].get("cost_spent", "0"),
                         "input_tokens": states[sid].get("input_tokens") if states[sid].get("token_usage_known") else None,
                         "output_tokens": states[sid].get("output_tokens") if states[sid].get("token_usage_known") else None,
                         "cost_status": "simulation" if providers[participant["model"]] == "mock"
                         else "calculated_or_reserved",
                         "trajectory_cost_usd": None if states[sid]["status"] == "needs_reconciliation" or
                                  (participant.get("parent") and states[participant["parent"]]["status"] == "needs_reconciliation")
                                  else str(amount(states[sid].get("cost_spent", "0")) +
                                           amount(states.get(participant.get("parent"), {}).get("cost_spent", "0")))})
    paired = []
    parents = [{"id": sid, "model": state["model"], "replicate": state["replicate"]}
               for sid, state in states.items() if state.get("generation", 0) == 0]
    for parent in parents:
        row = {"parent": parent["id"], "model": parent["model"], "replicate": parent["replicate"]}
        values = {condition: next((r for r in rows if r["session"] == parent["id"] + "-g1-" + condition
                                  and r["panel"] == "all"), None) for condition in ("control", "feedback")}
        available = all(v is not None and v["score"] is not None and v["failed"] == 0 for v in values.values())
        row["feedback_minus_control"] = values["feedback"]["score"] - values["control"]["score"] if available else None
        row["complete"] = available
        paired.append(row)
    # Resample independent conversation pairs, preserving all their fixtures together.
    deltas = {}
    for row in paired:
        if row["complete"]:
            deltas.setdefault(row["model"], []).append(row["feedback_minus_control"])
    interval = None
    if len(deltas) == len(config["models"]) and all(len(values) >= 2 for values in deltas.values()):
        rng = random.Random(0)
        draws = sorted(sum(sum(rng.choices(values, k=len(values))) / len(values)
                           for values in deltas.values()) / len(deltas) for _ in range(2000))
        interval = [draws[49], draws[1949]]
    groups = {}
    for row in rows:
        key = f"{row['model']}/g{row['generation']}/{row['condition']}/{row['panel']}"
        groups.setdefault(key, []).append(row)
    model_scores = {key: {"score": sum(r["score"] for r in values if r["score"] is not None) /
                         sum(r["score"] is not None for r in values) if any(r["score"] is not None for r in values) else None,
                         "replicates_present": len(values), "replicates_configured": config["replicates"]}
                    for key, values in groups.items()}
    total_cost = str(sum(amount(s.get("cost_spent", "0")) for s in states.values()))
    held = str(sum(amount(s.get("money_reserved", "0")) for s in states.values()))
    missing = [{"session": sid, "status": s["status"]} for sid, s in states.items() if "submission" not in s]
    result = {"rows": rows, "paired": paired, "model_scores": model_scores, "missing_sessions": missing,
              "cost_usd": None if amount(held) > 0 or any(s["status"] == "needs_reconciliation" for s in states.values())
                          else total_cost,
              "known_cost_subtotal_usd": total_cost, "reserved_usd": held, "interval_95_exploratory": interval,
              "incomplete": bool(missing) or any(r["failed"] for r in rows) or
                            any(s["status"] == "needs_reconciliation" for s in states.values()) or
                            bool(contemporaries and (contemporaries["failed"] or contemporaries["pending"])),
              "interpretation": "Exploratory bootstrap stratified by model, resampling conversation pairs with all fixtures, conditional on the frozen panel.",
              "pareto": [r["session"] for r in rows if r["panel"] == "all" and r["score"] is not None and r["cost_usd"] is not None and
                         not any(other["panel"] == "all" and other["score"] is not None and
                                 other["cost_usd"] is not None and amount(other["cost_usd"]) <= amount(r["cost_usd"]) and other["score"] >= r["score"] and
                                 (amount(other["cost_usd"]) < amount(r["cost_usd"]) or other["score"] > r["score"])
                                 for other in rows)]}
    write_json(out / "analysis.json", result)
    with (out / "analysis.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["session"])
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# G0/G1 comparison", "", "Mock providers" if all(m["provider"] == "mock" for m in config["models"])
             else "Real APIs: costs calculated from reported usage, billing not confirmed",
             "", "Scores against the same frozen G0 opponents and fixed controls on separate final seeds.",
             "", "| Session | Panel | Score | Matches | Failures |", "|---|---|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['session']} | {row['panel']} | {row['score']} | {row['completed']} | {row['failed']} |")
    lines += ["", "## Paired feedback minus control effect", "", "| G0 conversation | Difference |", "|---|---:|"]
    lines += [f"| {r['parent']} | {r['feedback_minus_control']} |" for r in paired]
    lines += ["", f"Total cost: {total_cost} USD; unresolved reservations: {held} USD.",
              "", "Missing results are retained in analysis.json. Scores are conditional on available submissions.",
              "Models are aggregated with equal weight per conversation. Same-model matches remain in the matrices.",
              "Intervals are exploratory, particularly with few conversations.",
              "", "[G0 matrix](tournament/report.md) · [G1 matrix](g1-tournament/report.md)"]
    text = "\n".join(lines) + "\n"
    (out / "analysis.md").write_text(text, encoding="utf-8")
    (out / "analysis.html").write_text("<!doctype html><meta charset='utf-8'><title>LLM Arena</title><pre>" +
                                       html.escape(text) + "</pre>", encoding="utf-8")
    return result
