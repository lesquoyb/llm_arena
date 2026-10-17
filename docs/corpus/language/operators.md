# Operators
> Tutorial

## Operators

Operators let you perform mathematical calculations and all kinds of data manipulation.

Here are the main operators:
- `+`: Addition of two numbers
- `-`: Subtraction
- `*`: Multiplication
- `/`: Division
- `\`: Quotient of the Euclidean division
- `%`: Remainder of the Euclidean division
- `==`: Equality between two values
- `<`, `>`, `<=`, `>=`: Comparison of two numbers
- `and`: "And" of two booleans
- `or`: "Or" of two booleans
- `=`: Assignment of a variable
- `+=`, `-=`, `*=` etc.: Operator + assignment of a variable

In an expression with several operators, the operators are applied from left to right, following the natural precedence rules, such as `*` taking precedence over `+`.

Example with different operators:
```
// Declare the variable a
var a
// Do a few calculations:
a = 2 + 8 // a takes the value 10
a = 5 - 4 // a takes the value 1
a = 3 * 5 // a takes the value 15
a = 6 / 2 // a takes the value 3
a = 8 % 3 // a takes the value 2

// Operators can be combined:
a = 1 + 2 * 3 // a takes the value 7
a = 4 / 2 + 1 // a takes the value 3
```

You can also use parentheses, as in: `(5 + 7) * 2`.

## Assignment operators

Besides the `=` operator, there are many assignment operators such as `+=`, `-=`, `*=` etc., which combine a calculation and an assignment.

An example with `*=`, which performs a multiplication and stores the result in the same variable:
```leekscript
var x = 5
x *= 3
// x is 15
```
