# LeekScript 4 syntax and state

`var` declares a variable. `if`, `while` and `break` control execution.
Arrays are zero-indexed. Game functions are global; Python or JavaScript imports
are not needed. `main.leek` is the entry point.
`include("lib/helper.leek")` loads a file from the same submission. Links and
paths outside that folder are refused. Sources allow 128 `.leek` files and 2 MB total.

Ordinary script variables do not preserve state between matches. Adapter registers
start empty for each match without PostgreSQL or global persistence.
`getAllies`, `isAlly` and `getEntity` distinguish teams and entities; consult
the signature reference for their arguments.
`say` costs 1 TP and has engine size/frequency limits. `listen` returns ID/message
pairs. This communication does not expose other sessions or their files.

Sources: LeekScript `8152f399faf7b418bbc5b2216d755c3822cda23b`,
`classes/EntityClass.java` and `engine/ArenaMain.java`. This guide covers the
included examples, not every language feature.
