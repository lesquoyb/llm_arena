# Local web interface

The interface and documentation are in English. Archived prompts and responses
keep their original text; the versioned experiment prompts under `prompts/fr`
remain in French.

The interface configures participants and competitions and reads the same
experiment artifacts as the CLI. It uses Python standard-library HTTP and
storage code. No separate database server, Node.js or Leek Wars service is needed.

## Start

Install the project first: [Windows](windows.md) or [Linux](linux.md).

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m arena ui --open
```

Linux:

```bash
.venv/bin/python -m arena ui --open
```

The browser opens **http://127.0.0.1:8765**. Keep the terminal open.
Ctrl+C closes the server and requests a stop of its active competition.
Use `--port 9000` for another port and `--runs PATH` for another results folder.
The server listens only on the local machine and is not a multiuser service.

Existing experiments under `runs` appear automatically. Archives remain readable
without their original runtime. Resume requires the original code, engine and
settings; **Clone configuration** starts a new run with current code instead.

## Offline demo

1. On **Overview**, click **Configure demo**.
2. Keep the two mock participants and choose a competition name.
3. Click **Calculate schedule**, then **Save configuration**.
4. Under **Competitions**, click **Launch**, then **Start competition**.
5. Open the run to inspect conversations, source versions, matches and results.

The complete demo plans 80 evaluation matches plus requested preparation matches.
For a shorter test, select **Initial strategy only**, one repetition and one seed.
Matches can take several minutes.

Mock participants use predefined scripts, not LLMs. Their diagnostics and Java
matches are real. The programmed improvement in the feedback branch demonstrates
the workflow; it is not evidence of learning or model quality.

## Participants

A profile stores a stable ID, provider, exact model ID, supported parameters,
per-call limits and dated prices. OpenAI, Anthropic, native Gemini and
OpenAI-compatible APIs are supported.

**Load models** fills the model selector using the configured API key. Choose
an entry or enter an exact ID manually if the endpoint has no catalog. Listing
models does not start a generation. The list does not supply prices or guarantee
that every listed model supports conversation tools.

Prices are **USD per million tokens**. An input price of 2 means $2 per million
input tokens. Enter current official prices and their date. Optional cache rates
fall back to the standard input rate when omitted.

Keys can come from the server environment, for example `ARENA_OPENAI_KEY`, or
from the password field. A key entered in the UI stays in server memory until
shutdown. It is not returned in API responses or written into profiles,
configurations or artifacts. Leaving the field blank keeps the available key.
Environment variables must be cleared separately in the system that supplies them.

New OpenAI and Gemini profiles default to model seed 0 where supported.
The seed is visible in the launch dialog and sent request. Some models or
compatible servers reject it. Clear the field for those models. Anthropic does
not expose a seed. A seed does not guarantee identical output; compare the full
request and backend metadata. See [provider details](providers.md#catalogs-seeds-and-request-records).

A run keeps a copy of its participant settings. Editing a reusable profile does
not change previous experiments.

## Competition settings

Choose participants, repetitions, evaluation of the initial strategy alone or with improvement branches, seeds, team size,
turn limits, entity stats, equipment and budgets. JSON import supports full
manifests. A repetition creates an independent conversation.

A match seed controls reproducible map generation and placement. Preparation
seed 17, feedback seeds and final evaluation seeds are separate. Mirrors compare
a strategy with itself and do not affect the ranked score.

All preparation limits are optional and blank in new competitions: calls, tools,
test matches, time, tokens and cost. A **Model call** is one API response,
including each response after tool results. A **Tool call** is one action requested
by that response. Counts, usage, elapsed time and cost are recorded even without
limits. Models may use different amounts of preparation to reach their submissions.
Anthropic still requires an explicit per-call output cap. Existing configurations
and demos retain their limits. Paid launches require API authorization and show
whether a financial limit is configured. One response can exceed a configured
financial limit; accounting reservations are not provider billing guarantees.

**Team setup** switches between shared rosters and independently built teams.
Shared mode exposes the character editor. Participant mode hides it and lets
each LLM choose 1–4 members, individual levels (1–301), capital allocations,
equipment, components and alterations. Only official game rules apply; no
additional equipment limits or allowlists are offered in this UI. Explicit
level and capital are required for each submitted member, and omitted components
mean none. The internal reference roster is used for preparation opponents.
Free stats remain available for shared experimental rosters. See
[realistic stats](realistic-stats.md) for validation rules and sources.

Equipment selectors list the pinned player-equipment catalog. In realistic mode, items
above the leek level are locked and cannot be selected, including by models.
Lowering the level removes newly ineligible selections with a notice. Free mode
allows all player-equipment levels. Selectors support name/ID searches and
show level, AP cost, range, line of sight, effects and the raw definition. Empty
default equipment means no items. Weapons use runtime `item` IDs and chips use
catalog keys; replay events use template IDs. Each field's question mark provides its help once, without repeating it beneath
the field. Help opens the interface,
authoring, rules and pinned API documents without leaving the application.

`configure_team` writes `team.json`, which is hashed and frozen with sources.
It creates a version in **Code & versions** and is inherited by both improvement
branches. The exact team appears in recorded tool calls, submissions and match
scenarios; changing sides preserves the chosen team. All member scripts are
included in submission analysis.

One managed competition runs at a time. **Stop** keeps checkpoints. **Resume**
checks them and reuses completed work. An API call with an unknown outcome keeps
its reservation and requires reconciliation with provider billing; it is not
retried blindly. The run log shows errors and execution details.

Deleting a profile or saved configuration does not delete results. **Export**
creates a separate copy with a file and hash inventory. Exports are excluded
from cross-competition aggregates.

## Source history and files

**Code & versions** reconstructs source files after each successful write tool
call. Select a conversation, version and file, then compare against an earlier
version or the empty state. Failed write proposals remain in the conversation
but do not create versions. Improved versions include inherited writes from the initial strategy.

**Open conversation** jumps to the matching messages. Git is not needed in each
participant folder: the journal already preserves file contents and hashes.
The viewer is read-only. Tournaments that received scripts directly show their
frozen sources without inventing intermediate edits or generation prompts.

**Files** previews and downloads sources, diagnostics, settings, logs and reports.
Use **Raw** or **Rendered** for Markdown and JSON. Markdown supports basic
headings, lists, links, tables and code blocks; embedded HTML is escaped. JSON
uses a collapsible tree. Large rendered previews are truncated, with the full
content available in Raw view or as a download.

Static engine resources are hidden by default. Check **Include static engine data**
to show them. This does not hide generated source folders named `data`.
`data/forbidden_words.txt` comes from the pinned upstream Leek Wars repository.
The local adapter does not load it through `Censorship.setSwearWords` or use it
to moderate LLM conversations. It is retained as part of the engine inventory.

## Conversations and journal

**Conversations** shows complete recorded prompts, responses, tool calls and
results, with pagination. **Follow live** moves to new messages.
New calls include a **Sent request** section containing the full messages,
tool schemas and model parameters, plus a canonical JSON SHA-256.
The request intent is recorded before execution, including when the call fails.
Authentication values are redacted.

Mocks use the same `respond(history, tools, output_limit)` interface and record
the prompts and tools they receive. Fixed evaluation controls supplied directly
as `.leek` files have no generation conversation. Old archives are not rewritten
to add request records that were never saved.

Native API fields, usage, request IDs and available backend/model versions are
preserved. Internal reasoning is shown only when the provider returns it.
**Journal** adds execution events and timestamps. Opening an event checks the
artifact SHA-256 against the journal.

## Matches, statistics and matrix links

**Matches** supports stage, participant, opponent, outcome and text filters.
Wins and losses use the selected participant as their reference, regardless of
which side it occupied. Without a selected participant, they use side 1.
Text search matches participant IDs and seeds.

In **Summary**, the match matrix shows row-against-column wins, draws and losses.
Click a count to open those fights. Failure counts open failed matches; a score
opens completed matches in its denominator. Links preserve the exact stage and
both participants and exclude mirrors. Filters remain in the URL, so a view
can be reloaded or shared. **Clear filters** restores the full match list.
A zero count opens an empty filtered list rather than selecting an unrelated fight.

The schematic replay supports play/pause, speed, stepping and seeking. It shows
positions, HP, attacks, healing, deaths and recorded resurrections. It does not
reproduce all official client effects or animations. Raw events and final engine
metrics remain available, including failures without replays.

Statistics include computation, actions, shots, chips, weapon changes, movement,
cells moved, damage, healing, erosion, deaths, errors and operation-limit hits.
Use **Metrics** to switch between overview, computation, actions, damage and all
columns. Match views show totals for the match, teams and leeks, plus per-turn
and per-leek details. Summary totals and matrices are separated by stage.
Actions count moves, weapon changes, shots and chips; automatic effects are not
counted as decisions. AP/MP removed refers to replay events, not all resource spending.

The operation budget is `min(2147483647, entity.cores * 1000000)` per played turn
and leek. The viewer reads it from the match scenario; the demo uses 10 cores,
so its limit is **10,000,000**. This differs from the generic AI fallback constant.
Missing limits are shown as unavailable rather than guessed.

New adapter telemetry attributes damage and healing to their source, including
delayed effects. Old archives may lack per-turn operations, per-leek errors or
source attribution. Missing values stay `N/A`. Old replay damage can include
overkill. Historical operation totals may assign summons to their summoner;
new per-entity telemetry separates them.

## Scores and comparisons

The initial strategy produces two improvements: **Improved without feedback**
and **Improved with feedback**. Only the latter receives match results. Both branches inherit the same initial strategy code and history.
Score is `(wins + 0.5 * draws) / completed matches`, excluding mirrors. A score
of 70% is not necessarily a 70% win rate. A score difference of 0.4 is 40 percentage points.

Panels distinguish all reference opponents, frozen initial strategies and fixed
handwritten controls. Compare versions against the same panel. Contemporary
initial and improved strategy standings remain separate. Mock cost zero means no API calls; machine
cost is not included. Operations are not tokens. Missing costs stay unknown.

**Compare results** averages fixed-opponent scores with equal weight per complete
conversation. Incomplete conversations are counted separately. Runs group only
when scenario, final seeds, opponent sources, preparation budgets and corpus,
scientific engine identity and mock/real mode match. Model parameters are part
of model identity. Exports are not counted twice.

## Development and updates

After changing the Java adapter, rerun the platform bootstrap and restart the
server. Existing results remain readable. Resume still requires their original
code and runtime; clone settings to run them with current code.

```bash
python -m unittest discover -s tests -p test_web.py -v
python -m unittest discover -s tests -p test_web_metrics.py -v
```

These tests cover histories, HTTP protections, keys, budgets, protocol grouping,
metrics and, with the engine built, worker stop/resume and cached result reuse.
They are included in Linux and Windows validation.

The **Local web interface** workflow uses Node 22, Playwright 1.62.1 and Chromium
for browser checks. Those are development dependencies only.
`node scripts/test-ui.cjs` tests synthetic archives and writes screenshots to
`runs/ui-browser`. `ARENA_BROWSER_EXECUTABLE` selects an installed Chromium.
`ARENA_UI_LIVE_ENGINE=1` also launches and monitors a mock competition with the real engine.

### Summons and example combat

The engine supports summon chips and their LeekScript callbacks. In Matches,
summons appear at the successful creation event, with square markers and their
own health cards. Their turns, movement, damage and deaths are replayed. Rewinding
before creation hides them again. This remains a schematic replay; inspect raw
events for effects without animations. See the [runnable example](../examples/showcase/README.md).

Equipment selectors use generator runtime IDs: weapons use the raw catalog's
`item` field, while chips use its object keys. Replay weapon/chip actions use
`template` IDs, translated to names in the event list. Earlier UI versions used
weapon catalog keys in the selectors and could equip a different weapon or none.
Reselect weapons in affected saved configurations before rerunning them. The
original default weapon ID 37 remains the pistol. Historical results are retained.

Realistic equipment capacity is per leek: 2 weapons below level 100, 3 from 100,
4 from 200, and one chip per RAM point. The stat preview shows this capacity.
The participant equipment caps are additional competition restrictions, not
substitutes for these limits. Default equipment must fit every default member;
participant-selected equipment uses each member's own resulting RAM.

Boss/internal chips (411–419, 425) and summon-only abilities (444–447) are
excluded from player loadouts in every mode, including free mode. They are hidden
from selectors and the model-facing chips catalog. Existing configurations using
them must be edited before launching again; they cannot bypass validation by
setting an allowlist or using participant-selected teams. The upstream data
remains intact so native summons and historical replay labels continue to work.

## Scenario presets and character sheets

New competitions start with **Simple duel**: one level-300 leek per side, up to
1,000 turns, no chips, and four direct-damage weapons (pistol, magnum, rifle,
rhino). These weapons have no poison, persistent effects or passive effects and
use single-cell areas with unrestricted launch directions. The legal 1,680
capital is fully allocated: 700 strength, 570 life, 150 AP, 120 MP and 140 cores.
The resulting build has 2,957 HP, 600 strength, 14 AP, 6 MP and 5 cores. Life and
strength cannot both be maximized independently within the same capital budget.
Saved configurations and the short offline demonstration retain their own settings.

The roster uses character tabs. Each card has a name, level, prominent final
stats, remaining capital, stat sliders and independent weapon/chip selectors.
Sliders and numeric fields change **final stats**, not capital. The engine's tier
costs determine the allocation; the tooltip gives the next attainable increase
and its price. The range shows what that stat can reach at this level if all
capital were assigned to it. The shared remaining-capital meter identifies
overspending, which is rejected on save. Equipment capacity and level checks use
each individual member's build. Both sides receive the same default roster;
participant-selected teams can still choose different builds under the shared rules.

**Dream team · saved preset** loads a fixed local roster. Selecting it never
contacts LeekWars. The bundled file is `data/presets/dream-team.json`; a manual
refresh/import creates a local override in `.arena/ui/dream-team-preset.json`.
Every competition freezes its own copy, so refreshing never changes an existing run.

The one-time development fetch and the optional **Refetch current top farmer**
button use the current public active farmer talent ranking, not the ranking of
teams/compositions. The first farmer is looked up dynamically. Four public leeks
are selected by talent, then level and ID if ties need resolving. Today the user
observed farmer 512 with leeks 599, 881, 1549 and 11942; these identifiers are not
hardcoded in the fetcher. Fewer than four public leeks causes an explicit error.
The farmer endpoint wraps its profile in `farmer`; the importer unwraps it.

The snapshot preserves real levels (including 301), published final stats, item
IDs and item order. Imports use free stats because public totals can include
components. Published final totals are preserved unchanged. Public component
templates and alteration deltas are retained without applying bonuses a second
time. Checking Realistic stats validates exact capital, component charge/capacity,
levels and equipment while keeping all final totals. A failed validation keeps
the free build unchanged and explains the mismatch. These
are public builds, not private combat scripts. Missing stats, private loadouts,
non-player chips or unsupported equipment abort the import and retain the old preset.
The original payload, date, ranking entry, selected IDs and hash are saved.

To populate the bundled preset once during development, run where LeekWars is
reachable (the cloud currently receives HTTP 403):

```sh
python scripts/import_dream_team.py --save-preset
```

An existing snapshot can be frozen without another request:

```sh
python scripts/import_dream_team.py --snapshot dream-team-public.json --save-preset
```

Commit the resulting data file. **Refresh or replace the saved Dream team** in
the UI permits an explicit refresh or a pasted JSON snapshot for a local override.
The bundled file now contains a frozen public snapshot of Pink, CoLeek, Veggy
and Zombizou, including component instances and alteration deltas. It works
offline and passes realistic validation without changing the published totals.

When **Participants choose teams and equipment** is selected, the character
editor and competition equipment restrictions disappear. Every LLM chooses
1–4 members, individual levels (1–301), names, scripts, capital, equipment and
component alterations under official game rules. There is no imposed character
stat allocation or equipment allowlist. Every submitted member must declare
its own level and capital; omitted components mean none. The internal fixed
reference roster is used only as the preparation opponent, not as the build
for submitted teams.

**LLM builds its team** is the third preset. Each participant chooses 1–4 leeks,
with independently chosen levels from 1 to 301 and an explicit capital allocation for each member. It chooses
names, scripts, weapons and chips. Capital follows each chosen level (1,780 at level 301); RAM controls
chip slots and level controls weapon slots. Non-player items remain forbidden.
This realistic builder supports base stats plus capital, with components and validated alteration charge/capacity. The visible default roster supplies fixed reference opponents; it
is not forced onto participant submissions.

The LLM receives two read-only tools, available through native APIs and MCP:

- `preview_build({level, capital, components?, member_index?})` returns final stats, remaining
  capital, equipment slots and the cost of the next stat increases.
- `validate_team({members})` checks the complete draft and reports errors.
  Scripts need not exist yet; missing entrypoints are reported separately.

It then writes the scripts, calls `configure_team` to save the validated build,
and uses `analyze`/`test` against the real engine. `configure_team`, test and
submission repeat validation, so skipping a preview cannot bypass the rules.
No inherited capital or raw-stat overrides are accepted in this preset.

Matches above 64 turns use the arena's documented engine build extension:
`engine/leekscript.init.gradle` compiles a source overlay with a 1,000-turn event
ceiling and finalizes draws at the requested scenario limit. The pinned upstream
checkout stays unchanged. Rebuild the engine after updating this version; existing
runs remain viewable but cannot be resumed under a different engine identity.
