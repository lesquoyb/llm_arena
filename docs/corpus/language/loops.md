# Loops
> Tutorial

We're now going to look at another type of structure that's just as fundamental as conditions: loops!

A loop lets you repeat instructions several times. There are several types, bounded and unbounded, which we'll cover in this part.

## `while` loop

The unbounded `while` loop has a syntax similar to the `if` we saw earlier. It runs a block of instructions as long as a condition is met.

Here's an example:
```
// Declare a counter and initialize it to 0
var counter = 0
while (counter < 5) { // As long as the counter is less than 5
    counter++ // Increase the counter by 1
    debug("Counter is " + counter)
}
```

When it runs, this code displays the following in the logs:
> Counter is 1
Counter is 2
Counter is 3
Counter is 4
Counter is 5

## `do while` loop

The unbounded `do while` loop is similar to the while loop, except that the condition comes at the end, so the body of the loop always runs at least once:

```
var x
do {
    x = rand() // x is a random number between 0 and 1
} while (x < 0.8) // repeat as long as x isn't greater than 0.8

debug("x: " + x) // displays a number between 0.8 and 1
```

A possible output of the program:
> x: 0.85712

## `for` loop

The `for` loop is a bounded loop that looks like a while loop, but more compact. With practice, you'll see that depending on the situation, a for or a while is more convenient.

The for loop is made of three optional parts:
- **The initialization**: assigning a starting value to a `counter` variable;
- **The condition**: as long as it holds, the loop keeps running;
- **The increment**: increasing (or decreasing, depending on the case) the value of your `counter` variable.

Example of a `for` loop:
```
// Loop from i = 1 as long as i is less than or equal to 5
// and increment i on each pass through the loop
for (var i = 1; i <= 5; i++) {
    debug("Counter i is: " + i)
}
```
This code displays the following in the logs:
> Counter i is: 1
Counter i is: 2
Counter i is: 3
Counter i is: 4
Counter i is: 5
