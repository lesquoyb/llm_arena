# Writing an arena strategy

The engine runs LeekScript 4. `main.leek` contains the logic for one entity turn.
Game functions are available globally without imports. In shared-team mode, all members run the same entry point and share the scenario
equipment. Participant-team mode lets you choose the
team size, equipment, stat builds and per-member entry points under `scenario.team_selection`.
Write the sources first, then call `configure_team` with `members`, each containing
`entrypoint`, `weapons` and `chips`. Optionally set `capital` per member in
realistic-v1 mode (official level/capital rules, no components), or `stats` in
free mode. Read corpus/stat-rules.json. Omitted stat overrides inherit the
corresponding default member build. Use weapons.json `item` values as weapon IDs (pistol: 37), and chips.json keys as chip IDs (shock: 1). Weapon catalog keys and replay template IDs are different identifiers. Read
slot limits and allowlists in the initial message. In realistic mode, items cannot exceed member level; free mode permits higher-level items.
Call `test` to evaluate your current team and `submit` to freeze code and `team.json`.
Do not write team.json directly; the tool validates and records each change.

Action points (`getTP()`), movement points (`getMP()`) and operations
(`getOperations()`) are separate resources. Operation budgets are
`min(2147483647, cores * 1000000)` per turn. The default 10 cores give 10 million
operations. Return control before exhausting that budget.

Example tested with the demo equipment:

```javascript
var enemy = getNearestEnemy()
if (enemy >= 0 && isAlive(enemy)) {
    setWeapon(getWeapons()[0])
    moveToward(enemy)
    while (getWeaponCost() >= 0 && getTP() >= getWeaponCost() && isAlive(enemy)) {
        if (useWeapon(enemy) != USE_SUCCESS) break
    }
}
```

`getNearestEnemy()` returns -1 when there is no enemy; do not assume null.
`getWeapons()` lists equipped weapons. `setWeapon` selects one; `moveToward`
spends movement points; `useWeapon` attempts a shot. Check `USE_SUCCESS` to
avoid looping on an out-of-range or blocked shot. This example assumes at least
one equipped weapon.

Support files must be part of the same submission. For example,
`include("lib/targeting.leek")` loads an internal file. The resolver refuses
external files and opponent files. Registers start empty for each match and
do not persist across matches. Submissions allow 128 `.leek` files and 2 MB total.

After installation, using the project Python:

```bash
python -m arena analyze path/to/my-strategy
python -m arena fight path/to/my-strategy examples/strategies/rush
```

Analysis success does not imply effective gameplay. Inspect `outcome.json`
for replay events and game logs, and `result.json` for compact results and team
metrics. Commands print the output path.

The [pinned reference](leekscript-v1/api.md) provides signatures and declared base
costs. Equipment data is in `weapons.json`, `chips.json` and `summons.json`.
The [API guide](corpus/api-guide.md) explains the example functions. Unlisted
behavior is not implied by a function name.


For participant-built teams, `preview_build` calculates final stats from capital
and `validate_team` checks the full proposed loadout without saving it. Scripts
may be absent during the dry run; configure_team requires them. If
`scenario.team_selection.require_capital` is true, provide capital for every
member explicitly. The `llm-team` preset fixes levels at 300 and permits up to
four members. Names, scripts, weapons and chips can differ per member.
