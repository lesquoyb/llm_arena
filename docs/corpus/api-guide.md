# API contracts for the pinned engine

Arena runs LeekScript 4. Game calls are global, without imports. Use lookup_api with query for one exact name/fragment, or queries for up to 20 searches in one tool step. For example, lookup_api({"queries":["getCell","getDistance","moveToward"]}). Discover available names with lookup_api({"mode":"index","kind":"functions"}); the index omits definitions. Follow next_offset/continuation for more matches. Each query in a batch has its own continuation. Under a small call budget, group related missing signatures rather than making repeated lookups. Its square brackets describe positional arguments: `getEntity[] => integer` means `getEntity()`. A nullable type such as `integer?` does not mean an argument is optional; separate signatures describe different arities.

## Execution

The entrypoint's top-level statements run once each entity turn. Helpers execute only when called. There is no automatic main or nextTurn callback, and no finishTurn API is needed: execution ends when the top-level program finishes. Design your own combat decisions; this guide documents interfaces rather than a strategy.

## Common calls

| Call | Contract | Declared base operations |
|---|---|---:|
| getEntity() | Active entity's runtime ID, including a summon on its own turn. getLeekID() is a different persistent ID. | 5 |
| getNearestEnemy() | Geometrically nearest living enemy's runtime ID, or -1 if absent. | 25 |
| isAlive(entity_id) | Whether a known entity is living. | 15 |
| getWeapons() | Array of equipped weapon runtime IDs, not objects. | 50 |
| setWeapon(weapon_id) | Select an equipped weapon; false if absent or invalid. | 15 |
| getWeaponCost(weapon_id) | TP cost; -1 if unknown or absent. The no-argument overload uses the selected weapon. | 15 |
| useWeapon(entity_id) | Attempt an attack with the selected weapon; integer result, compared with USE_SUCCESS. Invalid targets can return -1. | 3000 |
| moveToward(entity_id) | Move toward an entity; returns movement performed. A second argument limits MP used. Null produces a warning without movement. | 500 |
| getTP() | Remaining TP. | 15 |

An isolated equipment-query example is `var equipped = getWeapons();`. Each array element is already a weapon ID: no getWeaponId conversion is needed. Arrays use count(array), not array.length.

Weapons use the catalog's item field as runtime IDs. The outer catalog key, id and template fields are different identifiers. For example weapon item 37 is pistol. Chips use chips.json keys. Replay action identifiers may be templates instead.

Declared operation costs are not necessarily total costs; movement also charges operations in its implementation. TP, MP and operations are distinct resources. Check action return codes and ensure loops terminate on failure or lack of progress. Equipment ranges, line of sight, launch restrictions and usage limits matter independently of TP. Do not infer undocumented effects or formulas from names.

## Chips and summons

getCooldown(chip) gives remaining cooldown. getChipCooldown(chip) gives configured cooldown duration. Before casting, account for equipped chips, remaining TP, cooldown and target validity. canUseChip checks targeting and does not replace TP or cooldown checks.

summon(chip, cell, callback, name) creates an allied entity whose callback runs on its turns. It requires a summon chip and a valid empty placement cell. The callback sees the summon's own equipment and resources; getSummoner() identifies its owner. Consult exact signatures and the summon catalog before implementing callbacks.

## Verification and testing

Save code and call analyze promptly. Read diagnostic_messages and repair errors, then analyze again. Reaching status valid proves compilation, not effective tactics or freedom from runtime errors. Reanalyze after subsequent edits and before submit.

Preparation uses the actual pinned Java engine. test defaults to passive, training seed train-17, and both starting sides. To compare your own alternatives, save two source files and supply entrypoint and opponent_entrypoint to test. In participant-team mode the opponent copies your roster and uses the alternate entrypoint on every member; your saved team is unchanged. Hidden opponents and evaluation seeds are not exposed.

Use the returned test_id with read_replay to inspect fight actions, team_metrics, turn_metrics or logs, including debug output and runtime errors. These tools expose your own preparation artifacts only. A passive-opponent win is not evidence of strength against an active opponent.

Documentation and replay reads are character-paginated. Follow returned continuations for required complete reads. The initial prompt does not embed all equipment data or signatures; consult relevant catalogs and references instead of guessing.
