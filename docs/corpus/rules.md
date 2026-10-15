# Rules and preparation catalog

Teams have equal size, stats, weapons and chips. The manifest fixes equipment,
which is supplied in the initial prompt. Each member runs the same entry point
on each of its turns. Engine winners are sides 0 or 1, with -1 for draws.
Replay teams are numbered 1 and 2. Mirrors are diagnostics outside the main score.

TP limits actions, MP limits movement, and cores sets the per-turn operation
budget to `min(2147483647, cores * 1000000)`. RAM limits LeekScript memory;
the Java heap is a separate safeguard. Engine duration may reach `max_turns + 1`
at the turn limit. Timings measure elapsed time, not CPU time.

The default map has 613 cell IDs, 0 to 612. Obstacles block placement and affect
paths and visibility. `getDistance` measures geometric distance;
`getCellDistance` measures grid distance, not necessarily a traversable path.
Weapons need equipment, enough TP, valid range and line of sight as defined
in their data. Check the return code of `useWeapon`.

Public preparation uses `scenario_id: training`, `seed_id: train-17` and
`opponent_id: passive`. `test` runs both sides and consumes two matches.
Feedback and final evaluation seeds are separate and cannot be requested through
`test`. Compare G1 against the same frozen G0 panel and fixed controls.

Sources: pinned generator `Fight.java`, `maps/Map.java`, `classes/FieldClass.java`,
`state/State.java` and `fight/entity/EntityAI.java`. This is an original source
summary; game data and signatures remain attributed to Leek Wars / LeekScript.
