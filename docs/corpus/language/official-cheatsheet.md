The original sheet uses placeholders (...). In Arena, include only files inside your submission. Registers do not persist across matches; editor pause/mark helpers are not required. Prefer cheatsheet.md for adapted, complete syntax examples.

# LeekScript Cheat Sheet
> LeekScript

> This page sums up how to use LeekScript and is aimed at experienced players. If you are a beginner, see the Tutorial (corpus/language/index.md).

LeekScript (corpus/language/index.md) is an **imperative**, **functional**, **object-oriented** and **weakly typed** language inspired by JavaScript, PHP and Java.
In Leek Wars, it runs on the server to generate the fights. Every instruction uses up operations, and the limit is set to 1 million operations per leek core (getMaxOperations), per fight turn.

#### Variables
```
var a = 12 // local variable
global b = 'hello' // global, kept from one turn to the next
```

#### Conditions and loops
```
if (a > 12 and a < 20) {
	for (var i = 0; i < 10; ++i) { ... }
} else if (a != null)
	while (a > 0) { a-- }
```

#### Lists

```
var a = [1, 2, 3, 4]
a[2] = 10
var b = [ [1], [2], [3] ] // two dimensions
for (var value in a) { ... }
for (var index : var value in a) { ... }
```

Main functions: count, push, pop, insert, inArray, arrayMap, sort, etc.

#### Maps
```
var t = [ 'key1': true, 'key2': false ]
t['key3'] = 100
mapRemove(t, 'key1')
for (var key : var value in t) { ... }
var emptyMap = [:]
```

Main functions: mapSize, mapContainsKey, mapContains, mapRemove, mapKeys, mapValues, etc.

#### Functions
```
function computeDamage(weapon, strength, target) { // Named function
	return getDamage(weapon) * strength - getAbsoluteShield(target)
}
arrayMap([1, 2, 3], function(v) { // Anonymous function
	return v ** 2
})
```

#### Classes
```
class Cell {
	private static SIZE = 17 // static field
	public x // field
	public y
	constructor(x, y) { ... } // constructor
	distance(cell) { ... } // method
}
var myCell = new Cell(5, -7)
myCell.distance(otherCell)
```
More on this in Objects and Classes (corpus/language/objects-classes.md).

#### Debugging your code
```
debug("Value of my variable = " + myVariable) // Shows up in your personal logs
mark(myCell(s), COLOR_BLUE) // colors one or more cells
clearMarks() // clears the marks
pause() // Pauses the fight
setRegister('data', myData) // saves data from one fight to the next
```

#### Using several files
```
include('other.leek')
include('../folder/functions.leek')
```
