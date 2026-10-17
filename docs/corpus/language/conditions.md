# Conditions
> Tutorial

In the previous chapter, we saw how to boost ourselves, give ourselves a shield and heal ourselves. You've probably noticed that boosting and protecting yourself is always useful, but healing is pointless when your life is already at its maximum.

To avoid casting a heal and wasting TP , we'll use **a condition**, which is written like this:
```
if (getLife() < getTotalLife()) {
	useChip(CHIP_BANDAGE)
}
```

This code casts Bandage only if we're hurt, that is, when our current life `getLife()` is less than `<` our maximum life `getTotalLife()`.

A condition is built like this:
 - The `if` keyword
 - A condition **in parentheses**, here `(getLife() < getTotalLife())`
 - The body of the condition, **in curly braces**, here `{ useChip(CHIP_BANDAGE) }`. It runs if the condition is true.

## if else

You can also write code that runs when the condition is false, using the `else` keyword:
```
if (getLife() < getTotalLife()) {
	useChip(CHIP_BANDAGE)
} else {
	useChip(CHIP_HELMET)
}
```

This code casts Bandage if we're hurt, and Helmet otherwise.
