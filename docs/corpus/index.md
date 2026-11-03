# Shared corpus, protocol 1

## Accessing the references

Use `read_docs` for this shared corpus, `authoring.md`, and `leekscript-v1/` references. `read_file` reads your own workspace sources only. A missing-file error from `read_file` on a documentation path does not show that the reference is unavailable; use `read_docs` with the same path.

For example:

```json
{"path":"corpus/language/cheatsheet.md"}
```

These are arguments to `read_docs`. Follow returned continuation calls when a required read is truncated.

Use `lookup_api` with `query` for one name/fragment or `queries` for up to 20 grouped searches in one tool step. A space-separated string is not a batch. `lookup_api({"mode":"index","kind":"functions"})` lists function names without definitions; use `kind:"constants"` for constants. Follow each result's continuation for more matches.

## Reference map

- `rules.md`: turns, resources, map, teams and preparation catalog.
- `api-guide.md`: control-strategy functions, arguments and errors.
- `language/cheatsheet.md`: dense LeekScript 4 syntax, without a combat-strategy template.
- `language/index.md`: short official tutorial chapters by topic.
- `syntax.md`: includes, state and communication in Arena.
- `authoring.md` (read_docs root path): required authoring and submission contract, with isolated language examples rather than a worked combat strategy.
- `leekscript-v1/api.md` (read_docs root path): all signatures and declared base costs.
- `leekscript-v1/{weapons,chips,summons,components}.json` (read_docs root paths): pinned equipment.
- `components.md` and `component-levels.json`: per-leek base component rules and public item levels.

Each experiment freezes this corpus by hash. Do not invent undocumented behavior.
Resolve ambiguities against generator commit
`b99a174dd938260d9e47b2e65a208cb32230e26e` while preparing the corpus, not by
accessing the web during an experimental session.
