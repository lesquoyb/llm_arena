# Standard functions
> Tutorial

A **function** is used to perform a task such as a calculation or an action. It takes arguments as input, executes instructions and can return a result.

In our current code, we use the following functions:
 - `setWeapon(weapon)`: it has **1** parameter, and returns nothing.
 - `getNearestEnemy() → enemy`: it has **0** parameters, and returns the nearest enemy.
 - `moveToward(target) → mp`: it has **1** parameter, and returns the number of MP used.
 - `useWeapon(target) → success`: it has **1** parameter, uses the equipped weapon on someone and returns the result of the attack.

## The documentation

There are more than 300 standard functions in LeekScript, and they are all gathered on one page: **the documentation**. To get there, go to the Help tab, then click Documentation.

	<p>You can open the documentation from any page with the shortcut <b>Ctrl + Alt + H</b>. Try it now!
	</p>

The description of a function gives you the following information:
- A description of what the function does
- The list of its parameters, with their type and description
- The return type of the function and a description of what it returns
- Examples, notes and related functions.

## Using chips

Now that we are familiar with standard functions, we are going to use a few more in our AI!

A chip is a power you can use in a fight to heal, protect yourself, boost yourself, attack and more. To use one, you first have to equip it on your leek:

Then, use the `useChip(chip)` function to use a chip. Unlike weapons, chips don't need to be equipped in your code beforehand.

Buy the Bandage, Motivation, Protein and Helmet chips and equip them on your leek.

We will use all of them at the start of our turn, by adding the following code after equipping our weapon:
```
useChip(CHIP_MOTIVATION)
useChip(CHIP_PROTEIN)
useChip(CHIP_HELMET)
useChip(CHIP_BANDAGE)
```

`CHIP_MOTIVATION` and `CHIP_PROTEIN` are, like `WEAPON_PISTOL`, **constants** representing the chip or weapon you want to use. They are predefined values, listed in the documentation just like functions.
