# Shared corpus, protocol 1

- `rules.md`: turns, resources, map, teams and preparation catalog.
- `api-guide.md`: control-strategy functions, arguments and errors.
- `syntax.md`: basic syntax, includes, state and communication.
- `../authoring.md`: complete example and submission contract.
- `../leekscript-v1/api.md`: all signatures and declared base costs.
- `../leekscript-v1/{weapons,chips,summons,components}.json`: pinned equipment.

For `read_docs`, paths start with `corpus/` or `leekscript-v1/`.
Each experiment freezes this corpus by hash. Do not invent undocumented behavior.
Resolve ambiguities against generator commit
`b99a174dd938260d9e47b2e65a208cb32230e26e` while preparing the corpus, not by
accessing the web during an experimental session.
