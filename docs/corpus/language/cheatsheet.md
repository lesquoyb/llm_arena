# LeekScript 4 quick reference

Use this syntax, not Python or assumed JavaScript syntax. Examples below teach
language features only; they are not a combat strategy.

## Values and declarations

```leekscript
var amount = 12;
var ratio = 2.5;
var label = "hello";
var enabled = true;
var absent = null;
integer typedAmount = 12;
global remembered = null;
```

`var` declares a local variable; explicit types are optional. `global` preserves
one entity's state across its turns in the same fight. Arena starts fresh for
every fight; registers do not provide cross-fight persistence. `// line comments`
and `/* block comments */` are supported. Use semicolons consistently.

## Conditions and loops

```leekscript
var total = 0;
for (var i = 0; i < 4; i++) {
    if (i == 2) continue;
    total += i;
}
while (total > 0) {
    total--;
    if (total == 1) break;
}
if (total == 0) { total = 1; }
else if (total > 5) { total = 5; }
else { total += 1; }
```

Arithmetic: `+ - * / % **`; integer division: `\`. Comparisons: `== != < <= > >=`.
Boolean operators: `and`, `or`, `not` (also `&&`, `||`, `!`). Assignment: `=`,
`+=`, `-=`, `++`, `--`. A missing enemy ID is often `-1`, not `null`: check the
particular game's function contract. Bound loops by resources and progress.

## Arrays and maps are different in version 4

```leekscript
var values = [10, 20, 30];
push(values, 40);
values[0] = 11;
var size = count(values);
var sum = 0;
for (var value in values) { sum += value; }
for (var index : var value in values) { sum += index; }
var scores = ["left": 10, "right": 20];
scores["other"] = 30;
var emptyMap = [:];
for (var key : var value in scores) { emptyMap[key] = value; }
```

Array indices start at 0; arrays are dense. Append with `push`; assigning an
unused index does not grow the array. Empty array: `[]`. Empty map: `[:]`.
Use `mapSize`, `mapContainsKey`, `mapKeys` and other `map...` functions for maps.
Do not assume `.length`, `.append`, `.push()` or JavaScript array methods exist:
standard library functions such as `count(values)` and `push(values, item)` are global.

## Named and anonymous functions

```leekscript
function add(left, right) { return left + right; }
var twice = function(value) { return value * 2; };
var result = add(2, twice(3));
```

Parameters are declared inside parentheses; the body is a brace-delimited block.
`return` returns a value. A function value can be passed as a callback. See
`corpus/language/functions.md` for the full declaration explanation.

## Objects and classes

```leekscript
var point = {x: 2, y: 3};
point.x = 4;
class Pair {
    public x;
    public y;
    constructor(x, y) { this.x = x; this.y = y; }
    public sum() { return this.x + this.y; }
}
var pair = new Pair(2, 3);
var result = pair.sum();
```

`{x: 2}` is an object with named fields. `["x": 2]` is a map. JSON-style quoted
object property names are not interchangeable with LeekScript object syntax.
Classes use `constructor`, `new`, fields and methods; use the dedicated chapter
before attempting inheritance, access modifiers or static members.

## Files, debugging and compilation

Game functions are global, without imports. `include("lib/helpers.leek")` includes
an existing file in your submission. Paths outside the submission are forbidden.
`debug(value)` writes personal logs; inspect them with `read_replay` after `test`.
Online editor pause/visual helpers are not necessary to compile an Arena strategy.

After editing, call `analyze` on the actual saved entrypoint. Fix the readable
compiler diagnostics, then analyze again. Do not paste `...`, undefined names or
an isolated tutorial fragment as a complete script. To learn a specific topic,
read `corpus/language/index.md`; to call a game function, consult the separate
`leekscript-v1/api.md` reference. Successful compilation is not proof of good tactics.
