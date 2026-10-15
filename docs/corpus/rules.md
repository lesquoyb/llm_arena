# Rules and preparation catalog

The manifest declares the team-building mode in the initial prompt. Without
`scenario.team_selection`, teams have equal size, stats, weapons and chips and
members share the submission entry point. With participant selection enabled,
each model chooses 1..scenario.team_size members,
per-member entry points, equipment and stat builds using `configure_team`.
In realistic-v1 mode, allocate per-member capital under corpus/stat-rules.json
(level base stats plus capital, without components). In free mode, provide raw
per-member stats. Omitted overrides inherit the default member build. Write the source
files first. Equipment must satisfy slot limits and any allowlists. Realistic mode rejects
weapons and chips above the leek level, including default equipment; explicit
free mode permits higher-level items.
Use `item` values from leekscript-v1/weapons.json (pistol: 37), and keys from chips.json (shock: 1). Replay actions use template IDs instead. A selection is required
before test or submit. Successful selections create team.json, frozen with code
and inherited by improvement branches. Fixed reference opponents use the default
scenario team and equipment. Engine winners are sides 0 or 1, with -1 for draws.
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

## Equipment capacity and special items

In `realistic-v1`, each leek has 2 weapon slots below level 100, 3 at levels
100–199 and 4 at level 200+. Its RAM stat is also its chip slot count: RAM 6
allows 6 chips, independently of the memory budget used during script execution.
Per-member capital allocations therefore affect chip capacity. Competition caps
can restrict equipment further; they never increase realistic capacity. Shared
loadouts must fit every default team member. Free mode keeps engine experiments
possible without these player-style restrictions.

Sources: the pinned official client `src/component/group/group.vue` (weapon
thresholds), `src/component/leek/leek.vue` (chip count compared to `total_ram`)
and `src/component/leek/loadout-dialog.vue` (loadout validation), at commit
`2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9`.

The generator catalog is not a list of obtainable player items. Apocalypse (418)
is an exceptional example: level 1 is engine metadata, not proof of market
availability. In this snapshot it costs 5 AP, has one use per turn and applies
instant death over AREA_ENEMIES. It does not kill the caster. Player obtainability
has not been verified, so the arena excludes it from realistic builds and marks
it as special in the equipment selector; it remains usable in explicit free mode.
This exception is not a complete audit of every catalog item's obtainability.
