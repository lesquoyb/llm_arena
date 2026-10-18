# Lists
> Tutorial

A **list** lets you store several values in a specific order.

## Creating and using a list

You can create a list with the following syntax:
```
var list = [1, 2, 3, 4, 5]
```
The first position in a list is **position 0**. You access a specific element of the list with:
```
list[0] // Get the first element
list[2] = 10 // Assign the value 10 to the 3rd element
var a = list[3] + list[4] // add up the 4th and 5th elements into the variable a
```

Many functions for working with lists are available in the "Lists" section of the Documentation. The most notable ones are:
```
count(list) // size of the list
push(list, x) // adds an element x at the end
insert(list, x, position) // adds an element x at a position
remove(list, position) // removes the element at a position
inArray(list, x) // checks whether the element x is in the list
sort(list) // Sorts a list
```

## Iterating over a list with the `for in` loop

You can iterate over each value of a list with a simple `for` loop, like this:

```
var list = [10, 20, 30, 40, 50]
for (var i = 0; i < count(list); i++) {
	debug(list[i])
}
```

But there's a variant of the `for` loop that makes iterating over each value of a list simpler: the `for in` loop. The following code does the same thing as the previous one, but more concisely:

```
var list = [10, 20, 30, 40, 50]
for (var element in list) {
	debug(element)
}
```
