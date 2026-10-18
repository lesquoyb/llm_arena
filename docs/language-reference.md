# LeekScript language reference

Arena freezes the language documentation alongside every new experiment. Models
read it through the existing `read_docs` tool. No extra skill installation,
provider-specific tool or live website access is needed during preparation.

The starting prompt points to a compact [Arena cheat sheet](corpus/language/cheatsheet.md)
and a [topic index](corpus/language/index.md). The cheat sheet adapts the official
syntax to the local runtime and uses complete, small examples rather than a full
combat strategy. The strategy in authoring.md is optional to reduce the incentive
to copy one demonstration as every model's solution.

The 14 additional English chapters are sourced from the public Leek Wars
encyclopedia. They cover variables, booleans/null, conditions, operators, strings,
loops, lists, functions, objects/classes, typing, strict mode and version 4 changes,
as well as the original cheat sheet. Their short source explanations are retained;
website widgets, quizzes and full AI listings are omitted. Some chapters stop
before game-specific strategy examples to keep the language reference focused.
The exact extraction boundary, article ID, authors and source/rendered hashes are
recorded in [language-sources.json](language-sources.json), outside the model corpus.

Sources:

- [LeekScript resource index](https://leekwars.com/encyclopedia/fr/LeekScript)
- [English resource index](https://leekwars.com/encyclopedia/en/LeekScript)
- [Original cheat sheet](https://leekwars.com/encyclopedia/en/LeekScript_Cheat_Sheet)
- [Official tutorials](https://leekwars.com/encyclopedia/en/Tutorial)
- [Official compiler](https://github.com/leek-wars/leekscript)

Public pages can evolve independently of the pinned engine. The adapted sheet
and local compiler are the reference for Arena's version 4. Public examples may
be incomplete or use online-only facilities: the original sheet's `...` are
placeholders, includes cannot escape the submission, registers do not persist
between Arena fights, and online editor settings do not change compiler settings.
Game function signatures remain separately pinned in leekscript-v1/api.md.

## Refreshing the public chapters

This is a development operation, never an automatic step when starting a run:

```bash
python scripts/import_language_docs.py --save-snapshot .arena/language-docs-source.json
```

On Windows use the virtual-environment Python, for example
`.\.venv\Scripts\python.exe scripts/import_language_docs.py`.
The importer requests English encyclopedia API pages, checks all expected chapter
boundaries before publishing, and updates the source manifest. Review upstream
changes against the pinned compiler before committing them. The curated sheet
and topic index are maintained separately and are not overwritten by the importer.

To reproduce the extraction without network access:

```bash
python scripts/import_language_docs.py --snapshot .arena/language-docs-source.json
```

API paths encode spaces in article titles. Browser URLs display those titles
with underscores; using browser slugs directly against the API can return 400.
Existing experiment corpora remain frozen. Clone configurations for a new run
when adopting updated documentation. The web interface can also make an [audited continuation](recovery.md), preserving the original frozen documents. CLI resume remains strict by default.
