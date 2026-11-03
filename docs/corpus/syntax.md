# LeekScript 4 syntax and state

For the language itself, start with `corpus/language/cheatsheet.md` and choose
a topic in `corpus/language/index.md`. These cover declarations, control flow,
arrays versus maps, functions, objects and classes.

`var` declares a variable. `if`, `while` and `break` control execution.
Arrays are zero-indexed. Game functions are global; Python or JavaScript imports
are not needed. `main.leek` is the entry point.
`include("lib/helper.leek")` loads a file from the same submission. Links and
paths outside that folder are refused. Sources allow 128 `.leek` files and 2 MB total.

## Integer identifiers are not interchangeable

Runtime entity IDs, cell IDs and equipment IDs can all have integer types, but
represent different things. The compiler may accept an integer in the wrong
domain without establishing that the call is meaningful.

`getNearestEnemy()` returns an opaque entity handle, or -1 when absent. Its
numeric magnitude does not encode distance, coordinates, health or initiative.
Arithmetic on that handle cannot measure proximity. `getCell(entity_id)` obtains
an entity's current cell; consult the API reference for distance and targeting
calls and supply the identifier domain each argument requires. Geometric distance
is not a guarantee of a traversable path, line of sight or legal attack.
Equipment IDs identify items, not entities or cells.

## State and communication

Ordinary script variables do not preserve state between matches. Adapter registers
start empty for each match without PostgreSQL or global persistence.
`getAllies`, `isAlly` and `getEntity` distinguish teams and entities; consult
the signature reference for their arguments.
`say` costs 1 TP and has engine size/frequency limits. `listen` returns ID/message
pairs. This communication does not expose other sessions or their files.

Sources: LeekScript `8152f399faf7b418bbc5b2216d755c3822cda23b`,
`classes/EntityClass.java` and `engine/ArenaMain.java`. This guide covers the
included examples, not every language feature.
