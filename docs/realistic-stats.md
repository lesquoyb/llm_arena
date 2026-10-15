# Realistic stats and per-leek builds

New competitions enable **Realistic stats** by default. Each leek has its own
allocation of capital at the competition level. Stats are calculated from that
allocation; entering an arbitrary final stat is only possible in **Free** mode.
Capital is a game resource for building a leek, not API spending or token usage.

This version supports **base stats plus capital, without components or
alterations**. It is a constructible subset of official builds, not an exhaustive
simulation of the online account, inventory, components, loadouts or economy.
Weapons and chips still use the pinned generator catalog and the competition's
level, slot and allowlist rules. In realistic mode, default equipment and
participant-selected items above the leek level are rejected by validation and
the engine. The selectors show them locked; free mode permits higher-level items.
Lowering the level removes newly ineligible selections and reports their names. Reference opponents use the default member builds.

## Official rules used

Rules are pinned to the official client commit
[`2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9`](https://github.com/leek-wars/leek-wars/tree/2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9).
The client identifies its cost table as a mirror of server constants.

- [Base stats and capital formulas](https://github.com/leek-wars/leek-wars/blob/2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9/src/model/capital.ts).
- [Conversion tiers](https://github.com/leek-wars/leek-wars/blob/2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9/src/model/costs.ts).
- [Official boundary examples](https://github.com/leek-wars/leek-wars/blob/2d1969d3339d0ac1dc0ba6bc239b66ec2691f6e9/src/model/capital.test.ts).

The snapshot, source hashes and conversion tables are in
[corpus/stat-rules.json](corpus/stat-rules.json), supplied to every participant.
The live website API could not be queried from the cloud; the rules above come
from the official public source, not a live account verification.

Levels range from 1 to 301. Available capital is
`50 + (level - 1) * 5 + floor(level / 100) * 45`, plus 95 at level 301:
50 at level 1, 590 at level 100, 1135 at level 200 and 1780 at level 301.
Unspent capital is allowed. Assigned capital that cannot purchase the next
increment does not create a fractional stat point, matching the official algorithm.

| Stat | Base before investment |
|---|---:|
| Life | `100 + 3 * (level - 1)` |
| Frequency | 100 |
| AP | 10 |
| MP | 3 |
| Cores | 1 |
| RAM | 6 |
| Strength, agility, wisdom, resistance, science, magic | 0 |

Strength and the other main characteristics gain 2 points per capital below
200 bonus, then 1 point up to 400, then cost 2 capital per point up to 600,
then 3 per point. Life and AP/MP/cores/RAM have their own tiers; the complete
tables are in the snapshot. You cannot independently maximize every stat.

## Configure each member

Expand **Leek 1**, **Leek 2**, etc. to assign capital. The preview shows capital
used/available and the resulting stats. Saving rejects allocations above the
level's capital and invalid levels. Team size changes add or remove member builds.
Switching from free to realistic mode resets builds to a valid allocation;
switching back keeps the calculated values as editable raw stats.

Participant-selected teams can override each member's `capital` in realistic
mode or `stats` in free mode using `configure_team`. Omitted overrides inherit
the corresponding default member build. For example, at level 100:

```json
{
  "members": [
    {"entrypoint": "attacker.leek", "weapons": [1], "chips": [], "capital": {"strength": 100, "cores": 140}},
    {"entrypoint": "support.leek", "weapons": [], "chips": [3], "capital": {"wisdom": 100, "life": 100, "cores": 140}}
  ]
}
```

The scripts must exist first. Capital and raw stats cannot be mixed. Team builds
are journaled in `team.json`, frozen with the code and inherited by improvements.
Each match's `scenario.json` records the actual stats used for every member.

Old configurations without `stats_mode` stay in free mode, preserving archived
scenarios and results. Starting a new competition enables realistic mode; cloning
or importing an old configuration preserves its explicit settings.

## What LeekScript RAM means

RAM is the memory allowance of the combat script for arrays, objects and other
tracked allocations. It is unrelated to the model's context window or API tokens.
Cores govern operations per turn; RAM governs retained script data. Exceeding it
produces a runtime memory error.

The pinned generator converts `min(RAM, 50) * 8,000,000` to tracked 64-bit units:
approximately 64 MB per point, or 384 MB at the base RAM of 6. This is engine
accounting, not a promise about actual physical memory. The Java process has a
separate heap safeguard. See `EntityAI.applyEntityBudgets` and LeekScript
`AI.MAX_RAM` and `AI.checkRamOverflow` in the pinned source.
