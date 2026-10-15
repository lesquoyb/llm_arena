# Components

Each leek can equip its own `components` list, independently of its script,
weapons and chips. Use item-template IDs (`template` in
`leekscript-v1/components.json`), not the catalog's internal object keys.
For example `[290, 313, 317]` adds 4 cores, 4 RAM, 1 MP, 20 agility and
subtracts 30 resistance. These bonuses are added after base stats and capital.
They do not consume capital or change the price of the next stat increase.
RAM bonuses increase chip capacity; cores increase the operation limit.

There are eight slots per leek. Each template can occur only once, but different
tiers of a component may coexist. Ordinary components consume one slot;
recovery core (406) and recovery RAM (407) consume three slots each.
The realistic builder enforces each component's minimum level, in
`corpus/component-levels.json`. That public snapshot was exported on 2026-10-15
from the official `data/get-all` API. Bonuses come from the pinned engine.
Slot and duplicate rules follow the pinned official client's `leek.vue`.

`preview_build` accepts `capital`, optional `member_index` and `components`.
It returns base stats, final stats, bonuses, occupied slots and remaining capital.
`validate_team` and `configure_team` accept a `components` array per member and
repeat these checks. Omit it to inherit the reference member's components; use
`[]` to explicitly equip none. Selections are frozen in team.json and the native
scenario; the engine receives the resulting final stats exactly once.

Realistic mode supports base components, not alterations. Negative main
characteristics from component penalties are permitted; life, cores and RAM must
remain positive, and AP/MP cannot be negative. Free mode treats raw stats as
already-final totals. Public imports preserve component templates and alteration
stat deltas as metadata without adding their bonuses again. Free-mode editing
adds or removes component bonuses from the currently displayed final totals.
Alteration legality and account inventory ownership are not checked.

To refresh only component levels, run:
`python scripts/import_component_catalog.py`.
The simple duel preset deliberately keeps its original equipment and has no
components selected; add them on any character sheet or let a participant choose.
