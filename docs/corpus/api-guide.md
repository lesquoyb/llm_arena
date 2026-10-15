# Control functions checked in the pinned engine

| Call | Arguments and return value | Declared base cost |
|---|---|---:|
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
