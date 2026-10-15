# Writing an arena strategy

The engine runs LeekScript 4. `main.leek` contains the logic for one entity turn.
Game functions are available globally without imports. Team members run the
same entry point; both teams use the stats and equipment set by the scenario.

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
