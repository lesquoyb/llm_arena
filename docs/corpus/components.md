# Components

Each leek can equip its own `components` list, independently of its script,
weapons and chips. Use item-template IDs (`template` in
`corpus/component-rules.json`), not the catalog's internal object keys.
For example `[290, 313, 317]` adds 4 cores, 4 RAM, 1 MP, 20 agility and
subtracts 30 resistance. These bonuses are added after base stats and capital.
They do not consume capital or change the price of the next stat increase.
RAM bonuses increase chip capacity; cores increase the operation limit.

There are eight slots per leek. Each template can occur only once, but different
tiers of a component may coexist. Ordinary components consume one slot;
recovery core (406) and recovery RAM (407) consume three slots each.
The realistic builder enforces each component's minimum level, in
`corpus/component-rules.json`. This freezes base stats, levels, capacities and
alteration parameters from one official `data/get-all` response. It takes
precedence over the older generator's `leekscript-v1/components.json`.
Slot and duplicate rules follow the pinned official client's `leek.vue`.

`preview_build` accepts `capital`, optional `member_index` and `components`.
It returns base stats, final stats, bonuses, occupied slots and remaining capital.
`validate_team` and `configure_team` accept a `components` array per member and
repeat these checks. Omit it to inherit the reference member's components; use
`[]` to explicitly equip none. Selections are frozen in team.json and the native
scenario; the engine receives the resulting final stats exactly once.

Realistic mode accepts base component IDs and altered instances, for example
`{"template": 382, "stats": {"tp": 1, "life": 12, "wisdom": -4,
"science": -2, "frequency": -5}}`. The instance's `stats` contains additive
deltas, not replacement stats. Template stats and deltas are added after capital.
The public rules give each stat a weight. Positive deltas consume their full
weighted charge; negative deltas refund one quarter. The resulting charge must
not exceed the component's published capacity. This example consumes 185 of
the motherboard's 320 capacity. Validation uses exact quarter points, without
rounding an over-capacity component into validity. `describe`/`preview_build`
report each component's calculated charge and capacity.

Negative main characteristics from component penalties are permitted; life,
cores and RAM must remain positive, and AP/MP cannot be negative. Free mode
treats raw stats as already-final totals. Public imports retain component deltas
without adding bonuses twice. Enabling realistic mode subtracts those bonuses,
recovers an exact capital allocation, validates capacity, equipment and levels,
and requires the recomputed totals to match. An invalid build is reported and
left unchanged. No published snapshot receives a validation exemption.

This validates equipped component end states using the public charge rules;
it does not simulate random forge attempts, prove a crafting history, or check
account ownership and inventory. Recipe families, efficiencies and gains are
included in the frozen corpus for reference, not used to invent a history for
an equipped instance.

To refresh component rules together, run:
`python scripts/import_component_rules.py`.
Use `--snapshot saved-response.json` for a repeatable offline import. The file
records the source URL, game-data version, timestamp, payload hash and pinned
official client revision for the charge formula.
The simple duel preset deliberately keeps its original equipment and has no
components selected; add them on any character sheet or let a participant choose.

## Tool workflow

Components are equipment selected before a fight, not LeekScript function calls.
In the participant-selected team preset, write `main.leek`, inspect the available
components with `read_docs({"path":"corpus/component-rules.json"})`, and preview:

```json
{"tool":"preview_build","arguments":{"level":300,"capital":{"strength":1000},"components":[290,313,317]}}
```

Use the same build in a complete member definition:

```json
{"tool":"validate_team","arguments":{"members":[{"entrypoint":"main.leek","level":300,"capital":{"strength":1000},"weapons":[37],"chips":[],"components":[290,313,317]}]}}
```

After validation succeeds, pass those same `members` to `configure_team`, then
`analyze`, `test` and `submit`. The preview and validation results tell you the
final stats, capacity and remaining capital. In fixed-team scenarios the model
cannot change equipment; the competition's character sheets set components.
