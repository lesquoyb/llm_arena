# Control functions checked in the pinned engine

The arena compiles LeekScript **4**. Use `lookup_api` for exact function signatures or to search by name fragment instead of reading the entire API. Signatures use square brackets to describe arguments: `getEntity[] => integer` means call `getEntity()`, not `getEntity[]`. `integer?` means nullable, not optional; separate signatures describe different arities.

| Call | Arguments and return value | Declared base cost |
|---|---|---:|
| `getEntity()` | Runtime ID of the active entity, including an invocation during its own turn. Use this for self-targeted chips.`getLeekID()` is a persistent website leek ID, not a replacement runtime ID. | 5 |
| `getNearestEnemy()` | ID of the geometrically nearest living enemy; -1 if absent. Do not assume null. | 25 |
| `getWeapons()` | Array of weapon IDs equipped by the active entity. | 50 |
| `setWeapon(weapon_id)` | Select an equipped weapon; false for an absent or invalid weapon. | 15 |
| `moveToward(entity_id[, mp_to_use])` | Move toward an entity; return movement performed. Null does not move and produces a warning. | 500 |
| `getTP()` | Remaining TP of the active entity. | 15 |
| `getWeaponCost([weapon_id])` | TP cost, using the active weapon when omitted; -1 if unknown or absent. | 15 |
| `isAlive(entity_id)` | True for a known living entity, false otherwise. | 15 |
| `useWeapon(entity_id)` | Attempt a shot; compare its integer result to `USE_SUCCESS`. An absent/invalid target can return -1. | 3000 |

Declared costs are not necessarily total costs. `moveToward` also charges
operations in its implementation. Weapon effects and ranges depend on
`weapons.json`. Do not loop on failed shots. Successful analysis does not prove
effective play or absence of runtime errors.

Example for an entity equipped with at least one weapon:

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

Sources: `FightFunctions.java` for signatures/costs, `classes/FightClass.java`
for targeting/movement, `classes/EntityClass.java` for equipment/TP/life and
`classes/WeaponClass.java` for costs and shooting, at the commit in `index.md`.
Other functions remain covered by the signature reference; their behavior is
not inferred from their names.

## Chips, summons and testing

`getCooldown(chip)` gives the remaining cooldown. `getChipCooldown(chip)` gives
its configured duration, not its remaining cooldown. Before casting, check the
chip is equipped, enough AP remain, cooldown is zero and targeting is valid.
`canUseChip` checks targeting and does not replace AP/cooldown checks.

`summon(chip, cell, callback, name)` creates
an allied entity whose callback runs on its own turns. Use an empty reachable
cell and a summon chip. The callback sees the summon's own equipment and resources;
`getSummoner()` identifies its owner. Choose callback behavior appropriate to
the summon's available equipment and resources.

Preparation tools run against the actual pinned Java engine. Use `analyze` to
check source code, then `test` to play training matches. Training currently uses
the passive opponent, seed 17 and both starting sides; arbitrary opponents and
seeds are not exposed by this tool. `test` returns summaries. Use its test ID with
`read_replay` to inspect `fight`, `team_metrics`, `turn_metrics` or `logs`, including
`debug` output and runtime errors. These tools expose only the participant's own
training artifacts, not other participants' private sessions.

The initial prompt includes scenario and tool descriptions. The full API reference,
equipment, summons and stat rules are available through paginated `read_docs`;
they are not all inserted into the prompt automatically. Read the catalogs and
relevant function signatures before choosing equipment or writing code.
