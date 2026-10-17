# Booleans and null
> Tutorial

You've seen that you can work with numbers, but LeekScript also has special values: null and booleans.

## The `null` value

**null** is a value that represents an empty or invalid value, or even an error, but it's different from the number `0`.

For example, the `getWeapon()` function returns the weapon your leek is holding, or `null` if you don't have a weapon in your hands.

You may have noticed that `setWeapon()` costs 1 TP per turn. You can limit its use to turn 1 with this condition:

```
if (getWeapon() == null) {
    setWeapon(WEAPON_PISTOL)
}
```

## Booleans: `true` and `false`

**Booleans** are two values: `true` and `false`. You can use them to represent anything that has two states, such as:
 - True or false
 - On or off
 - Yes or no
 - etc.

```
var a = true
var b = false
```

Examples of functions that use booleans:
  - The chipNeedLos function, for example, returns a boolean: `true` if the chip needs a line of sight, `false` otherwise (like the Spark chip).
  - The isAlive function returns `true` if the entity is alive and `false` otherwise.

Example: checking whether a chip needs a line of sight:
```
if (chipNeedLos(chip) == true) {
	// the chip needs a line of sight
}
```
