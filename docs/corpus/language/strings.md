# Strings
> Tutorial

## Strings

Strings (character strings) are a type of value used to represent text.

A string is written between *single* or *double* quotes:
- `var a = "hi"`
- `var b = 'hello world'`

## Operations on strings

Only one operator is available on strings: **+**, the *concatenation* operator, which "glues" two strings together:
```
var a = "Hello"
var b = "how are you?"
var c = a + ' ' + b // "Hello how are you?"
```

Many functions are available for strings, in the "Strings" section of the documentation. The main ones are:
```
length(string) // length of the string
charAt(string, position) // Gets the character at a given position
substring(string, start, len) // Extracts a substring of length "len", starting at position "start"
toUpper(string) // Converts all the letters to uppercase
```

Examples:
```
length("labyrinthe") // returns 10
charAt("pirate", 2) // returns "r"
substring("galactique", 2, 5) // returns "lacti"
toUpper("mafia") // returns "MAFIA"
```
