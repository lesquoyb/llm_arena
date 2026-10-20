# Laya proposal-check sanity check

Measured locally on CPU with `convaiinnovations/laya`, revision `7b928d828b7b0e022f929d9bd2e44165aa270148`.
The production questions and wrapper were used unchanged. Each input occupied
one window, with 196–298 reported input tokens including questions. These six
illustrative cases do not establish precision or recall on real proposals.

| Input | Supplied solution risk | Prescribed strategy risk | Check |
| --- | ---: | ---: | --- |
| compile guidance | 0.4320 | 0.5407 | inconclusive |
| remove tactics | 0.6280 | 0.4352 | inconclusive |
| api guidance | 0.6262 | 0.3573 | inconclusive |
| syntax example | 0.7330 | 0.4546 | inconclusive |
| complete strategy | 0.4225 | 0.4563 | inconclusive |
| tactical recipe | 0.4320 | 0.9255 | rejected |

The four harmless examples all remain inconclusive. A complete combat program
also remains inconclusive, while an explicit tactical recipe is rejected. This
exposes both weak discrimination and the workflow bug of treating uncertainty
as rejection. Automatic mode now revises only explicit rejections; inconclusive
results remain recorded and the candidate proceeds to evaluation. Thresholds
and raw model scores were not altered to fit these examples.

The boolean `noul` value is the probability of true; its direction is correct.
For long inputs the library aggregates boolean questions using the maximum
window score, which can increase false positives. No extra context was added.

## Exact input text

Each value was wrapped as `{"source": "system prompt", "added_instructions": text}`.
The two production questions are in `arena/calibration_guard.py`.

### compile guidance

```text
Read the language reference. Save your code, run analyze, fix compiler errors and explicitly submit. Choose and implement your own combat strategy.
```

### remove tactics

```text
Do not prescribe a combat strategy. Remove tactical recipes and complete combat loops from the instructions. Retain only language syntax, API documentation and tool usage guidance.
```

### api guidance

```text
Use getEntity() for your runtime entity ID. Do not confuse entity IDs with cells or distances. Check exact function signatures before calling them.
```

### syntax example

```text
Variables use var, for example: var counter = 0. Named functions use function name(arguments) { ... }.
```

### complete strategy

```text
Copy this complete combat strategy into main.leek: var enemy = getNearestEnemy(); if (enemy >= 0) { moveToward(enemy); setWeapon(37); while (getTP() >= 3 && isAlive(enemy)) { if (useWeapon(enemy) != USE_SUCCESS) break; } }
```

### tactical recipe

```text
Use exactly this combat strategy: stack all shield buffs first, heal whenever below 60 percent health, approach the weakest enemy, fire your highest-damage weapon until TP is exhausted, then flee behind cover.
```
