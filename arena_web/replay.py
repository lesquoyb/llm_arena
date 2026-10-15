"""Labels and coordinates for the pinned engine's public action format."""
from __future__ import annotations

LABELS = {0: "Début du combat", 4: "Fin du combat", 5: "Élimination", 6: "Nouveau tour",
          7: "Début du tour d'une entité", 8: "Fin du tour d'une entité", 9: "Invocation",
          10: "Déplacement", 11: "Élimination directe", 12: "Utilisation d'une puce",
          13: "Changement d'arme", 14: "Effet cumulé", 15: "Coffre ouvert", 16: "Tir",
          17: "Réveil", 18: "Sommeil", 100: "PA dépensés", 101: "Dégâts", 102: "PM dépensés",
          103: "Soin", 104: "Vitalité", 105: "Résurrection", 106: "Perte de force",
          107: "Dégâts nova", 108: "Renvoi de dégâts", 109: "Dégâts de vie",
          110: "Poison / contrecoup", 112: "Vitalité nova", 201: "Lama", 203: "Message",
          205: "Case indiquée", 301: "Effet d'arme", 302: "Effet de puce", 303: "Fin d'effet",
          304: "Modification d'effet", 306: "Réduction d'effets", 307: "Poisons retirés",
          308: "Entraves retirées", 309: "Durée d'effet modifiée", 1000: "Erreur moteur",
          1001: "Carte modifiée", 1002: "Erreur de stratégie"}


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
            label = f"Tour {turn}"
        elif code == 7 and len(action) > 1:
            actor = action[1]
            label = f"{names.get(actor, actor)} commence son tour"
        elif code == 10 and len(action) > 2:
            label = f"{names.get(action[1], action[1])} se déplace vers la case {action[2]}"
        elif code in {101, 107, 108, 109, 110} and len(action) > 2:
            label = f"{names.get(action[1], action[1])} perd {action[2]} PV ({LABELS.get(code)})"
        elif code == 103 and len(action) > 2:
            label = f"{names.get(action[1], action[1])} récupère {action[2]} PV"
        elif code == 5 and len(action) > 1:
            label = f"{names.get(action[1], action[1])} est éliminé"
        elif code == 16 and len(action) > 2:
            label = f"{names.get(actor, actor)} tire sur la case {action[1]} (résultat {action[2]})"
        elif code == 12 and len(action) > 3:
            label = f"{names.get(actor, actor)} utilise la puce {action[1]} sur la case {action[2]}"
        elif code == 13 and len(action) > 1:
            label = f"{names.get(actor, actor)} équipe l'arme {action[1]}"
        events.append({"index": index, "turn": turn, "actor": actor, "code": code, "text": label, "raw": action})
    return {"cells": [cell_position(i, width) for i in range((2 * width - 1) * height - (width - 1))],
            "events": events, "unknown_codes": sorted(unknown),
            "note": "Relecture schématique : positions, PV, tirs, soins et éliminations. "
                    "Les effets détaillés et animations du client officiel ne sont pas reproduits. "
                    "Le journal brut reste la référence."}
