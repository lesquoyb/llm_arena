# Typing
> LeekScript

Since update 2.38, you can use types in LeekScript (corpus/language/index.md).

## Types

- `void`: no type
- `any`: any value
- `null`: null value
- `boolean`: Boolean value
- `integer`: whole number
- `real`: real number
- `BigInteger` / `big_integer`: whole number of arbitrary size
- `string`: character string
- `Array`, `Array<X>`: list, or list of values of type X
- `Map`, `Map<K, V>`: map, or map with keys of type K and values of type V
- `Object`: object
- `Function`, `Function R>`: any function, or a function that takes arguments of types A and B and returns a value of type R.
- `Class`: class
- Every class created by the user is a type.

### Compound types

Use the `|` sign to create compound types: for example, `integer | string` represents a value that can be either an integer or a string.

You can combine as many types as you like: `integer | boolean | string | Array`, for example.

To write a compound type with `null`, such as `Array | null`, you can write `Array?`.

### Typing a variable

```
var a = 12 // type `integer` in strict mode, `any` otherwise.
integer a = 12 // type integer
```

### Typing a function

#### Standard function
```
function fun1(real x, string y) => string {
	return x + y
}

var fun2 = function(real x, string y) => string {
	return x + y
}

var fun3 = (real x, string y) => string {
	return x + y
}
```

#### Lambda (anonymous) function

```
var fun4 = (real x, string y) => string x + y

var fun5 = real x, string y => string x + y
```

### Typing a for loop

```
var map = [1: "a", 2: "b"]
for (integer k : string v in map) {

}
```

### Typing a class field

```
class Leek {
	integer id // integer type
	string name // string type
	params // type `any` by default
}
```

### Typing a method

```leekscript
class Leek {
	// Method that takes two integers and returns a list of integers
	public Array<integer> getReachableCells(integer from, integer mp = getMP()) {
		[...]
	}
}
```

## Typing operators

### ! operator

The `!` operator changes the type of a value by removing the `null` type. It does not convert the value, nor does it make using it any safer.
For example, for a type `integer | null`:

```
var cellX = getCellX(512) // type integer | null
var xInt = cellX! // type integer
```

You can use it in a chain of object accesses: `object.foo!.bar`
However, if `object.foo` is null, it will crash at runtime. Today, this operator is mostly useful for removing warnings in strict mode with typing, and for making sure a variable is not null at runtime.

```
integer? cell = getCell()
moveTowardCell(cell) // this line shows a warning
moveTowardCell(cell!) // this line is OK, but if cell is null, it will crash at runtime
```

### as operator

The `as` operator converts a value to any type, if possible:

```
any param = fun() // type any
var paramInt = param as integer // type integer
```
