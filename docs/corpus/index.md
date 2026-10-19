# Shared corpus, protocol 1

- `rules.md`: turns, resources, map, teams and preparation catalog.
- `api-guide.md`: control-strategy functions, arguments and errors.
- `language/cheatsheet.md`: dense LeekScript 4 syntax, without a combat-strategy template.
- `language/index.md`: short official tutorial chapters by topic.
- `syntax.md`: includes, state and communication in Arena.
- `../authoring.md`: optional worked strategy and submission contract.
- `../leekscript-v1/api.md`: all signatures and declared base costs.
- `../leekscript-v1/{weapons,chips,summons,components}.json`: pinned equipment.

For `read_docs`, paths start with `corpus/` or `leekscript-v1/`.
Each experiment freezes this corpus by hash. Do not invent undocumented behavior.
Resolve ambiguities against generator commit
`b99a174dd938260d9e47b2e65a208cb32230e26e` while preparing the corpus, not by
accessing the web during an experimental session.


- `components.md` and `component-levels.json`: per-leek base component rules and public item levels.
