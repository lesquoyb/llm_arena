# LeekScript 4
> LeekScript

LeekScript 4 is the fourth version of the LeekScript (corpus/language/index.md) language, released on July 1, 2022. This page sums up everything new in this version.

## Separate Array and Map

In LeekScript 1 to 3, arrays were both lists (`[1, 2, 3, 4]`) and associative arrays (`['a': 5, 'b': 12]`). From LeekScript 4 onward, these two roles are split into two different types: lists (`Array`) and maps (`Map`). These two new types perform better than the old shared type, and make code clearer.

An `Array` list is a continuous sequence of elements, starting at index 0. It is the equivalent of Java's `ArrayList` or C++'s `vector`. You can quickly access an element by its position, and insert or remove an element at any position.

- Unlike the old arrays, you can no longer create an element on the fly like this: `array[10] = v`.
- All LS and fight functions return this new list type (except getRegisters, which returns a `Map`).
- The new `Array` type uses all the functions in the "Arrays" category of the documentation.
- Accessing an element outside the list returns null and a warning.

A `Map` is an object that links a key to a value. It is the equivalent of Java's `HashMap` or C++'s `unordered_map`: the (key, value) pairs are not ordered. Keys can be of any type: number (integer or real), string, object, etc. You can quickly retrieve the value associated with a given key. This new type replaces the "associative" side of the old arrays.

- The new `Map` type uses all the functions in the "Maps" category of the documentation, which are prefixed with "map".
- There are two ways to create an empty map:
	- `var map = [:]`
	- `var map = new Map()`

## New list functions

- `arraySome(list, predicate)`: returns `true` if predicate returns `true` for at least one element of the list.
- `arrayEvery(list, predicate)`: returns `true` if predicate returns `true` for every element of the list.
- `removeAll(list, element)`: removes every "element" from the list.
- `arrayFrequencies(list)`: returns a map associating (element => quantity).
- `arrayChunk(list, size)`: returns a list made of sub-lists of size N.
- `arrayUnique(list)`: returns a new array without duplicates.
- `arrayRandom(list, n)`: returns a list of N random elements.

## Return of the RAM limit

Since the new lists and maps perform much better and use far fewer operations, a limit on RAM (the program's working memory) had to be brought back. With very few operations, you could otherwise easily fill gigabytes of RAM.

The RAM limit used to be set to 100 MB for each AI (entity + summons) per fight, which is 12,500,000 list, map or object elements. Since update [2.40](https://leekwars.com/forum/category-6/topic-11126), it depends on the entity's RAM stat: 8 million 64-bit units (64 MB) per RAM point, up to 50 points. This limit applies in LS4 because the old arrays don't use this RAM system: they don't need it, as they already use up plenty of operations.

The `getMaxRAM()` and `getUsedRAM()` functions are added so you can monitor your RAM usage in real time.

## 64-bit integers instead of 32

Integers are now stored on 64 bits instead of 32 (as in every previous version of LeekScript). This lets you calculate with larger numbers and gives you more bits for bitwise manipulation.

## Arrow functions

The "arrow function" syntax is now available, for a simpler way to write anonymous functions:

```

=> 12 // No parameters, returns 12
x, y => x + y // Two parameters, returns their sum
x, y -> x + y // Thin arrow
x => y => x + y // Takes a parameter x and returns a function that takes a parameter y and returns the sum of x and y.
```

## Default parameters

In constructors, methods and static methods, you can now give each parameter a default value:

## List range access and negative indices

New ways to access lists are added:
- Accessing the last elements: `list[-1]` returns the last one, `list[-2]` returns the second to last.
- Range access: `list[10:20]` returns a new list containing the elements from position 10 (inclusive) to 20 (exclusive).
- Range access with a step: `list[10:20:3]` returns the elements at positions 10, 13, 16, 19.
- Negative step: `list[20:10:-3]` returns the elements at positions 20, 17, 14, 11
- The `arraySlice(start, end, increment)` function, which replaces `subArray`, behaves the same as the `list[start:end:increment]` syntax.

## Change to the == operator, and === deprecated

The `==` operator, which performed some exotic and potentially confusing equality checks such as `1 == true` or `12 == [12]`, now behaves the same as the `===` operator, which is deprecated.

- If you only used `===`, you can safely replace them with `==`.
- If you used `==`, some of them may have been comparing numbers and/or booleans, and will need to be replaced with a more complex expression.

## Hexadecimal and binary numbers

You can write numbers in hexadecimal and binary, in addition to decimal (thanks to Karang for the PR):

`var a = 0xabcdef // 11259375`
`var b = 0b110110101 // 437`

## "_" number separators

You can write long numeric constants with underscore "_" separators, for example:

`var one_billion = 1_000_000_000`

## Callback argument order

In the arrayMap, arrayFilter, arrayIter, arrayPartition and arrayFoldLeft/Right functions, callbacks always take their arguments in the order (value, key/index). Previously, the order was (key, value) and (value).

On top of that, all these functions pass the array being traversed as the 3rd parameter.

Callbacks can therefore take any number of arguments: the missing values are replaced with `null`.

## Function changes

- The `end` position of the `subArray` function is now exclusive in LS4+.
- The `removeElement` function no longer leaves holes in LS4+.
- The `arrayFlatten` function no longer copies elements.
- The `assocReverse`, `assocSort` and `keySort` functions are removed, and `removeKey` is replaced by `mapRemove` in LS4+.
- Fixed the cost of `arrayMin`.
- `randFloat` is renamed `randReal`.
- `codePointAt(string, [index])`: returns the Unicode code point (an integer) at position index (or 0) in the string.

## Basic argument type checking

All the game's functions now have precise types, so errors can be reported when an argument is incompatible with the type a function expects.

Since type inference is still very basic and bound to evolve, these type errors are only warnings for now.

## Precedence of a = b = c

You can now write `a = b = c` without parentheses.

## Duplicate key in a map declaration

When declaring a map, an error (LS4+) or a warning is returned if a key appears twice:

## Function complexity in the documentation

The complexity of each function is shown in the documentation.

## JSON encoding/decoding of objects and new lists

The JSON functions `jsonEncode` and `jsonDecode` now handle the new lists and objects:

`jsonDecode("[1, 2, 3]")`: returns a new list

`jsonEncode({a: 2, b: 4})` / `jsonDecode("{a:2,b:4}")`: works with objects.

## Number functions

- `bitCount(x)`: returns the number of bits set to `1` in the number.
- `trailingZeros(x)`: returns the number of `0` bits at the end of the number.
- `leadingZeros(x)`: returns the number of `0` bits at the start of the number.
- `bitReverse(x)`: returns a new number with all the bits reversed from left to right.
- `byteReverse(x)`: returns a new number with all the bytes (groups of 8 bits) reversed from left to right.
- `rotateLeft(x, y)`: returns a new number with the bits shifted left by `y` (the bits pushed out come back in on the right).
- `rotateRight(x, y)`: returns a new number with the bits shifted right by `y` (the bits pushed out come back in on the left).
- `hexString(x)`: returns a string representing the number in hexadecimal.
- `binString(x)`: returns a string representing the number in binary.
- `realBits(x)`: returns the bits of the number as an integer.
- `bitsToReal(x)`: returns a real number from bits stored in an integer.
- `isFinite(x)`: tells whether the number x is finite.
- `isInfinite(x)`: tells whether the number x is infinite.
- `isNaN(x)`: tells whether the number x is a NaN value.
- `isPermutation(x, y)`: returns `true` if the number `x` is a permutation of the number `y`.

## Number constants

- `NaN`: constant representing a NaN value. X == NaN is always `false` (hence the isNaN function).
- `Infinity`: constant representing infinity. For its opposite, use `-Infinity`.
- `Integer.MIN_VALUE` and `Integer.MAX_VALUE`: minimum integer (-2^63 = -9223372036854775808) and maximum integer (2^63-1 = 9223372036854775807)
- `Real.MIN_VALUE` and `Real.MAX_VALUE`: smallest strictly positive real (4.9e-324) and maximum real (1.7976931348623157e308)

## `final` keyword for class fields

You can put the `final` keyword in front of a class field to indicate that this field can no longer be assigned once the object has been constructed. An assignment means using the `=` operator: you can still modify the content of the field if it is an object or a list, for example. For a final array field, you must therefore use `arrayClear(object.field)` instead of `object.field = []`.

## Integer division operators `\` and `\=`

The `\` and `\=` operators are added to perform integer (or Euclidean) division, for example:
```
10 \ 3 // 3 (integer)
```
Note that both numbers are converted to integers if they aren't already:
```
10.5 \ 3.8 // 3 (integer)
```

## Miscellaneous fixes and improvements

- Fixed a bug when a method parameter is captured.
- Static initialization now happens on turn 1 of each entity, instead of before the fight. So you can no longer use 20M operations before the fight, and this fixes a fight bug that occurred when the operation limit was exceeded during this initialization.
- Errors are located more precisely.
- `debug([10, "20", "hi"])` displays `[10, "20", "hi"]` instead of `[10, 20, hi]`.
- Fixed a bug when using `break` and `continue` in a function, outside a loop.
- Redefining a function is forbidden from LS4 onward.
- Fixed bugs with static methods used through `A['m']` and `var m = A.m`.
- Added an error when a method is declared twice in a class.
- The search function returns `-1` instead of `null` when the element is not found.
