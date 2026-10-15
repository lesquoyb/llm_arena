# Pinned engine audit

Generator commit: `b99a174dd938260d9e47b2e65a208cb32230e26e`.
LeekScript submodule: `8152f399faf7b418bbc5b2216d755c3822cda23b`.
Source audit date: 13 October 2026.

## Turn limits

`PolyglotEntityAI.java` defines a 5,000 ms per-turn wall-clock safeguard and
`MAX_WALL_CLOCK_TIMEOUTS = 3` before disabling an AI. This is not a three-second
limit. `setTurnWallClockLimitMs` configures the duration. The pinned source prefers
a deterministic statement counter from the custom isolate with calibration;
time-based counting remains a fallback. The optional polyglot runtime was not
validated in this implementation.

For LeekScript, `EntityAI.applyEntityBudgets()` sets operations to
`min(Integer.MAX_VALUE, cores * 1000000)` and RAM to `min(50, ram) * 8000000`
runtime units. `AI.MAX_OPERATIONS` is a fallback, not the effective entity budget.
An infinite-loop integration test confirms interruption and operation-limit
reporting with one core. The arena does not change these upstream rules.
A whole-worker timeout is an infrastructure failure, not a participant loss.

## Adapter behavior

Upstream `Scenario.fromFile` does not apply the custom map, example
`max_operations_per_entity` field or `ai_owner` as needed here. The adapter sets
the map, test context, team mode and side ownership explicitly. Budgets use
recognized entity attributes.

The arena replaces database-backed registers with empty, nonpersistent local
registers. It extends statistics with team totals and per-turn/per-entity
operation, damage, healing and error telemetry. Upstream sources remain unchanged.
The Gradle init script removes only the unused native polyglot binary dependency;
other Java compilation dependencies remain. The upstream Gradle 8.5 wrapper is
not used; this build requires Gradle 9.3.1 and JDK 25.

`data/forbidden_words.txt` is an upstream resource copied with the engine data.
The adapter does not load it as a filter for LLM conversations.

## Reading results

Engine winners use sides 0/1 and -1 for draws; serialized replay teams use 1/2.
Real matches with swapped sides test the conversion. Turn timings use
`System.nanoTime()` and measure elapsed time, not CPU time. Reproducibility hashes
exclude timings but retain actions, map, entities, operations and results.
Control fixtures verify local repeatability, not every possible strategy or
random/time API on every machine.

Sources: [generator](https://github.com/leek-wars/leek-wars-generator/tree/b99a174dd938260d9e47b2e65a208cb32230e26e)
and [LeekScript](https://github.com/leek-wars/leekscript/tree/8152f399faf7b418bbc5b2216d755c3822cda23b).
