The online editor settings described below do not configure Arena; its pinned compiler settings apply.

# Strict mode
> LeekScript

Strict mode is a LeekScript (corpus/language/index.md) option, which can be enabled in the editor, that changes the behavior of the language. It is intended for experienced players and is not recommended for beginners.

## History

Strict mode was released in update 2.38.

## Enabling it

Click the "LeekScript X" button at the bottom of the editor and tick the `Strict mode (advanced)` checkbox. As with the version of an AI, strict mode applies to the AI and all of its includes.

## Features

#### Fixed variable type

Variables initialized with the `var` keyword and a value keep the type of that value. The advantage is that you don't have to write the variable's type explicitly.

For example, without strict mode, you can write:
```
var a = 12 a = "hello"
```
But in strict mode, the same code returns an error:
*Failed to assign value '"hello"' of type 'string' to variable 'a' of type 'integer'*

The `var` keyword in strict mode is therefore equivalent to `var` in Java or `auto` in C++.

To still be able to assign a type different from the first value, you can give the variable the `any` type:
```
any a = 12 a = "hello"
```
This code works even in strict mode.

#### Accessing outside an array raises an error.

In strict mode, accessing outside an array raises an exception and therefore stops the AI instead of returning `null`.

This behavior is handy because the return type of an access to an `Array<X>` is then `X` instead of `X | null`. It also avoids silent behaviors where null values would be used in calculations.

#### More type warnings are returned.

In strict mode, many new warnings are returned:
- Dangerous conversion: for example, converting an `any` variable to `string`: a warning will be returned because the conversion may fail at runtime.
- Dangerous call: if the function is not always callable.
- Dangerous access: if the list or map is not always iterable.
- Dangerous field access: if the object does not always have the field, for example:
	```leekscript
	class A { field } class B { }
	var t = [new A, new B]
	t[randInt(0, 2)].field
	```
