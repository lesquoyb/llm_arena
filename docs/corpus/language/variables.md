# Variables
> Tutorial

Variables are a fundamental concept in every programming language. They are storage locations that keep values in memory so you can reuse them.

Variables can hold several types of values:
- Number: `12`, `5.59`
- String: `"hello"`
- Boolean (true or false): `true`, `false`
- List, Table (we will come back to these a bit later)
- `null`: the absence of a value

## Declaring a variable

To use a variable, you first need to declare it. You declare it with the `var` keyword, like this:
```
// Declare the "enemy" variable
var enemy
```

You can also give your variable a value at the same time, like this:
```
// Declare the enemy variable and assign it the value "getNearestEnemy()"
var enemy = getNearestEnemy()
```

## Using a variable

To use the value stored in a variable, simply write its name:

```
// Move toward the enemy
moveToward(enemy)

// Try to shoot them!
useWeapon(enemy)
```

In this first AI, line **5** declares the variable `enemy`, which is initialized with the value `getNearestEnemy()`, that is, the nearest enemy.

This `enemy` variable is then used on lines **8** and **11**, where its value is passed to the `moveToward` and `useWeapon` functions.

## Global variables

Variables declared with the var keyword last for **your leek's turn**. There is a second type of variable that keeps its value for **the whole fight**: global variables. To declare a global variable, simply use the `global` keyword instead of `var`:
```
// Declare the global variable myGlobal, with the value 42
global myGlobal = 42
```
Variables and global variables are used the same way in your code. In the rest of the tutorial, we will mostly use normal variables (sometimes called local variables).
