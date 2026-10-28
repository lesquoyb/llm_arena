# Local web interface

The interface, documentation and current experiment prompts are in English.
Archived prompts and responses keep their original text.

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

Choose participants, repetitions, strategy rounds, seeds, team size,
turn limits, entity stats, equipment and budgets. JSON import supports full
manifests. A repetition creates an independent conversation.

**Number of rounds** includes the initial round. One evaluates only the initial
strategy; two adds one improvement round; larger numbers keep improving each
track. There is no 2-round limit. From Round 2 onward, feedback and no-feedback
tracks continue separately from their own previous submission, without creating
more branches. Every participant finishes preparing before the round's tournament;
all tournament and reference fights finish before the next round starts.

Choose **Continue until I press Stop** for no round limit. Stop preserves completed
rounds, submissions and match records; Resume continues the same frozen study.
The schedule is open-ended in this mode. A missing submission or failed evaluation
pauses progression for recovery rather than silently excluding a participant from
all future rounds. Other optional budgets still apply. In JSON, `generations` is
the total round count, or `null` for manual stopping.

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

A provider's `stop` finish reason ends its response, not its Arena round. Without
an explicit `submit` tool call, Arena sends a visible reminder and continues the
conversation. After three reminders, another response without tools ends the
session as **No submission**, with an explanation. Existing files are not
submitted automatically when a response stops. Reminder responses count toward
usage and any configured budgets. Previously recorded runs remain unchanged.

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
and per-leek details. Summary uses shared filters for rounds, models and match category.
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

## Feedback conversations

New improvement conversations start fresh, with the scenario, a numbered preparation instruction and the previous submitted files in the workspace. Earlier conversations are not resent. Select an older session to inspect its archived messages; **Initial history** remains available in older runs that inherited their history. Older runs' structured feedback is rendered as a visible table rather than only inside the raw record. Recorded requests remain unchanged.

With feedback, the instruction includes a plain English previous-round result summary. `list_past_fights` lists that participant's non-mirror previous-round tournament fights. `read_past_fight` provides an explained overview, chronological public actions, own per-turn metrics and own debug/error logs, with pagination. No 16-fight or four-action cap applies. Opponent code, opponent debug logs, other participants' unrelated fights, later rounds and final reference tests are unavailable.

Initial and without-feedback sessions cannot call these tools, even by guessing their names or IDs. The shared tool service enforces the permission for both native provider calls and MCP; it also omits unavailable tools from discovery. Both branches retain their standard preparation tools (`analyze`, `test`, `read_replay`). Old runs keep the feedback they originally received; the expanded tools apply to new compatible runs.

## Scores and comparisons

The initial strategy produces two improvements: **Improved without feedback**
and **Improved with feedback**. Only the latter receives match results. Both branches start from the same initial strategy code for Round 2. Later rounds continue their respective code track with a fresh conversation and an explicit round number. Only the feedback track receives a previous-round result summary. The server never grants past-fight access to the no-feedback track.
The competition Summary uses one shared filter bar: **Round**, **Model** and **Matches** (Tournament or Reference tests). Filters apply to the ranking, evolution chart, matrix, usage and conversation details. The model filter selects the candidate; its opponents stay visible. Versions and repetitions are grouped by model.

The default view shows four indicators, a model ranking, evolution by version and a head-to-head matrix. Detailed metrics, conversations, accounting and methodology expand on demand. Numeric columns in detail tables can be sorted. Small matrices fit the available width; large matrices scroll within their own container. Full model names are available from abbreviated headers.

Score is `(wins + 0.5 * draws) / completed appearances`. The ranking pools the selected appearances for each model; a 50% score can mean all draws. Failures are displayed separately. A tournament fight contributes an appearance to each model, so appearance counts can exceed unique fight counts. The completed-fight indicator counts each selected fight once. Tournament mirrors and preparation tests do not enter the scores.

Round 1 is the initial submission. Round 2 has two alternative branches, with and without feedback. Tournament opponents may change between rounds; use Reference tests to compare against frozen initial submissions and built-in scripts. Reference tests count only the candidate side, including tests against its own initial strategy. The evolution chart uses the same selected matches and rounds as the ranking.

Matrix cells show score and wins / draws / losses from the row model's perspective. Click a result to open the relevant fights. Tournament diagonals are omitted because versions of the same model are grouped. The accounting section reconciles tournament, reference and diagnostic mirror counts for the whole competition; preparation tests are listed separately.

Cost and tokens describe preparation of the selected versions regardless of match category. Reported tokens are counted even at zero prices and without limits; missing usage remains unknown or is marked partial. Mock participants have no LLM tokens. Replay legends identify the models by side and color.

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


## Conversation troubleshooting and performance

Conversation cards show the sender and recipient, message order, tool request/result
links, and recorded timestamps. Older archives may have no message timestamps.
Provider failures appear above the conversation, including the available public
API error and retry/billing uncertainty flags. For older runs the reader retrieves
that error from the hash-checked journal. The run log has a **Copy log** button;
the report also lists session failures for new runs. A failed provider session can
leave a competition incomplete even when every available strategy fight succeeded.

Collapsed exact requests are fetched only when opened. Large tool results show a
bounded preview; their full records remain accessible. Live mode does not replace
the conversation while a detail is open. It polls only for active work or state
changes, and the paginated conversation no longer transfers each request's complete
prior history on every refresh.

The participant briefing contains only gameplay configuration, a named roster,
ID conventions and tools the model can actually use. Public farmer profiles and
fight histories remain in provenance and are excluded from new prompts. The
current templates are English; a legacy `prompt_language: fr` field is accepted
for configuration compatibility, but does not select old French templates.

Weapon baselines work with shared Dream team rosters and participant-selected
teams. Mock profiles configure a team through the same tools as API models; fixed
reference strategies use the scenario roster. They now handle empty weapon lists
and inspect all equipped weapons. They remain simple weapon baselines, not optimal
chip/summon strategies; feature-showcase demonstrates those APIs separately.

## Conversations and journal by model

Choose a **Model** in Conversations or Code & versions, then a conversation by
repetition and initial/improved strategy. Only that model's conversations appear
in the selector. **Conversation journal** opens the events for that exact thread.
The Journal also lets you select a model across all its conversations, or select
**All models** for the complete competition log. Events are filtered before
pagination and show their model and conversation; **Open conversation** returns
to the corresponding thread. Model/session filters are kept in the URL for
refresh, navigation and links, and changing a filter resets pagination.

## Retry one failed conversation

**Retry conversation** is available in the session list and beside the selected
conversation when it stopped without a frozen submission. It continues that
thread's saved history and files. Other models are not called again. Their
submissions, API usage and completed match artifacts remain unchanged. If an
initial strategy is recovered, its previously skipped improvement branches are
created from the recovered submission. New matches involving recovered entrants
are added to the existing tournament; old schedules are retained under history/.

A retry does not reset usage counters or extend budgets. API calls still require
the normal launch confirmation, for the selected model only. Unknown remote
outcomes or reserved billing must be reconciled first. Submitted strategies
(including invalid ones) cannot be replaced through retry after evaluation.
An exported archive is read-only. As with resume, the frozen configuration,
runner, engine, prompts and documentation must match the recorded experiment;
retry does not bypass provenance checks after an incompatible project update.

CLI: `python -m arena experiment retry runs/<competition> --session <session-id>`.
The journal records retry requests, prior checkpoint hashes and attempt counts.

Recovery keeps already produced feedback and improvement branches as they were;
it does not regenerate another model's history to include newly available results.

## Editable profiles, frozen runs and preparation matches

Saved competition configurations use the latest saved participant profiles when
opened, previewed and launched, including endpoint, model, prices and parameters.
Inline participants whose IDs are absent from the profile catalog keep their
embedded settings. The launch preview shows the resolved settings. If a profile
changes after that preview, launch is rejected until you review the updated
preview. A started competition freezes its resolved profiles; editing a profile
does not alter existing runs, retries, historical requests or results.

The execution order is:

1. Preparation: each model can edit, compile and request training fights against
   passive. These fights are explicitly unscored and cannot expose opponent scripts.
2. Initial round: submitted sources and team.json are frozen. The configured
   pairings run against those same submissions, without model calls between fights.
3. Improvement, if enabled: both branches start from the initial code, with fresh conversations; one
   gets the initial round's results and the control branch does not.
4. Improved round and reference evaluations: each branch's submitted code is frozen.

Matches defaults to **Competition rounds**. Choose **Preparation tests (unscored)**
to inspect training fights, **Reference evaluations (frozen scripts)** for the
common evaluation panel, or **All fights**. Training fights are excluded from
competition statistics and matrices, and have an explicit badge on their replays.
Their count is displayed separately. Configuring unlimited preparation lets a
model run more training tests until it submits; a training fight is not a round.

**Live updates** is enabled by default when opening a running competition and
is available in the common toolbar for every view. Refreshes follow journal and
match artifact revisions, even if no new model message or root report exists.
Matches, statistics, the journal, files and code versions update accordingly.
The checkbox pauses updates; its selection is kept while navigating that run.
Expanded conversation records, open dialogs and playing replays pause replacement
so they remain readable. Selected match/replay position, file and statistics stage
are preserved. Human labels use initial/improved strategy and feedback condition;
raw paths, IDs, original messages and provenance remain unchanged for auditing.

A **Submitted** conversation has frozen its sources; it does not certify compilation
or successful fights. Open **Diagnostics** in the overview's Conversations table,
or open the conversation, to inspect generation status, submission validation and
fight failures separately. The compilation report includes diagnostics from every
team entrypoint. Fight failures show the engine error, seed, participants and
artifact path. A missing validation or fight result is pending, not a failure.
Round 2 tournament and reference evaluation fights wait until both preparation
branches have finished, so a submitted branch can temporarily show only its
Round 1 fights while another branch is still working.

Conversation live mode appends new messages with a brief arrival animation and
smoothly follows them when you are at the bottom of the current conversation.
Existing message nodes stay in place. Scrolling up, inspecting an earlier page or
opening a record pauses following so the text you are reading stays put. A new
message indicator and Follow latest button let you catch up; returning to the
bottom resumes following when inspecting the live tail. Reduced-motion settings
disable the animation and smooth scrolling. The live view retains at most 200
message cards; earlier records remain available through Previous and the journal.
Each assistant response has its own recorded reasoning blocks, when the provider
returns them, followed by its tool requests and their receipts.

File tools show the requested path. A read identifies the character range actually
sent to the model, whether more text remains, and its next offset. Expand the
excerpt to read that content without the JSON envelope. A write shows a diff and
the full submitted text, reconstructed from that exact request, including older
runs whose receipt contains only a hash. Rejected writes are identified and do
not become the baseline for later diffs. If the preceding content was never
recorded, the interface says so instead of claiming an exact before/after edit.


## Model-facing document and replay views

Document JSON is compacted before pagination; source URLs, commit IDs and hashes
stay in the frozen corpus and journal rather than the model-facing view. Character
offsets refer to that compact view. Source code and meaningful Markdown line breaks
are preserved. Tool responses sent to providers omit internal hashes and provenance;
the exact outgoing request remains inspectable in the journal.

`read_replay` defaults to 16000 characters. A partial page explicitly reports
`truncated`, its character range and a complete `continuation` call. Repeat that
call until `next_offset` is null. The same test ID, side and section must be kept.
A partial JSON fragment is not a complete replay.

`list_past_fights` and `read_past_fight` expose only the previous round, labeled in
each result, and only to the feedback track. Calibration uses the same previous-round
scope for training fights; validation and audit fights remain hidden.
`list_submissions` and `read_submitted_file` provide earlier frozen code by explicit
round number, within the same track and replicate. These source-only tools are
available with or without feedback; they reveal no match results or opponent code.


## Language reference and private sparring

Models can read a dense LeekScript 4 sheet at `corpus/language/cheatsheet.md`
and choose an official tutorial topic through `corpus/language/index.md`.
The initial instruction points to syntax before implementation; the full strategy
in authoring.md is optional. See [language reference sources](language-reference.md)
for origin, extraction and manual refresh instructions.

The preparation `test` tool accepts `opponent_entrypoint` to pit two scripts in
the participant's own workspace against one another. It still runs both starting
sides and returns a normal replay ID. A participant can therefore write a
sparring strategy, or copy an earlier own submission, and examine the resulting
logs and metrics. Participant-team opponents mirror the candidate roster and
run the alternate script for every member, without editing the candidate's team.
The Matches view labels these opponents by their source entrypoint. These are
preparation tests, not scored competition fights. No other model's sources are
readable through this mechanism.

### Reuse submitted strategies

In a competition, open a conversation or the overview's conversation table and
choose **Save as participant**. Give the frozen strategy a unique participant ID.
It then appears in **Participants** and can be selected in another competition.
The code, entrypoint and participant-selected team are copied and fingerprinted,
so deleting the source run does not remove the participant. No API key, model
call or generation charge is required. Every round uses the same saved files.
The original scenario is required to preserve equipment/build semantics: clone
the source competition and replace its participant selection. A mismatch is
reported before launch. Saved participants are inspected rather than edited;
save a newer submitted version under a new ID to replace a strategy.

**Participants > Add reference strategy** adds a fixed opponent for the default
single-leek scenario: passive, stationary shooter, one-shot pursuer, aggressive
shooter, or the Apache-2.0 human weapon heuristic. Their descriptions state what
they do. They are not Elo ratings and are not guaranteed to be ordered by strength.

Model ranking and progress charts exclude matches between versions of the same
model, including earlier rounds and feedback tracks. Those fights remain in the
strategy-version matrix and match list. Click the ranking's win/draw/loss counts
to inspect exactly the matches contributing to that number.

### Saved providers and bulk participants

In Participants, open **Providers & bulk add**. Save a named protocol, endpoint and
API key environment variable. A key entered here stays in server memory until
shutdown; set the named variable in the repository-root `.env` file to reuse it after restarting. Copy `.env.example` to get started.
The connection settings are saved in `.arena/ui/providers.json`, without the key.

Choose a saved provider, load its models, select the models to add, and enter each
model's input/output prices in USD per million tokens (0 for free/local models).
Each participant gets its own editable ID and pricing. Anthropic also requires
an output token maximum. Creation validates the entire selection before saving;
existing participant IDs are never overwritten. Loading models does not generate
text or establish that a listed model supports tools.

For individual models or parameter variants, choose **Add participant**, then a
**Saved provider**. Adjust the model, reasoning settings and prices as usual.
Participants copy the connection settings at creation. Editing or deleting a
saved provider does not modify existing participants or frozen competitions.

## Workspaces

Use **Workspaces > New workspace** to separate tests and benchmark campaigns.
The sidebar selector scopes Overview, Competitions and Compare results. Participant
profiles and provider connections remain shared. Existing competitions start as
**Unassigned**; no files are moved or rewritten.

Open a workspace and choose **Add existing competitions** to organize existing runs and
saved configurations. Each item belongs to one workspace. Selecting an item from
another workspace moves it; unchecking an item already here makes it unassigned.
You can also move one run using the workspace button under its name in the run
history. The competition editor has a workspace selector; runs launched from a
saved configuration inherit its workspace. Moving a configuration later does not
move its previous runs. Deleting a workspace only unassigns its members.

The workspace page shows recorded costs, reservations, submission validity,
measured tokens, messages and preparation time across its competitions. Resources
are summed once per conversation. Missing token measurements remain marked, and
reserved money is separate from recorded cost. Exported copies are excluded.
These are recorded estimates using configured prices, not provider billing totals.

Performance charts keep different scenarios, engines, preparation settings,
rounds and configured opponent pools in separate comparison groups. Reference
panels also require matching archived opponent hashes. Tournament matches between
versions or repetitions of the same participant are excluded from model scores;
mirrors and preparation fights are excluded too. Model variants with different
participant IDs remain distinct. The score is an equal-weight mean of each
conversation's completed-fight score (win 1, draw 0.5, loss 0). Engine failures
are shown separately. An evolving tournament score measures performance against
that pool, not improvement against a constant benchmark.

**Download CSV > Workspace scores** exports the displayed aggregate scores and
their comparison group IDs. The other downloads preserve raw match results,
strategy results and conversations for the workspace's original competitions,
including same-participant fights. Each fight has two side rows in the match
CSV. Use the conversation CSV to total costs; costs repeated across result stages
must not be added together. Calibration studies remain in their separate workshop.
Workspace metadata lives in `.arena/ui/workspaces.json` with other local UI settings.

## Participant groups

In **Participants > Groups**, create groups such as Local, Free APIs or Paid.
Select any number of existing profiles for each group. A profile can belong to
several groups. Use **Groups** on a profile card to edit its memberships, or the
list filter to browse a group. Groups are shared across workspaces, like profiles.

In the competition editor, choose **Add participants from group > Add group**.
This adds the group's profiles to the current selection without removing other
profiles or creating duplicates. You can add several overlapping groups, clear
the selection, and still select individual profiles. Groups organize participant
profiles, so two parameter variants of the same model can have different groups.

The selection is copied into the competition configuration when saved. Changing,
renaming or deleting a group does not change existing configurations or running
competitions. Deleting a profile removes it from groups. Deleting a group keeps
all profiles. Group metadata is saved in `.arena/ui/participant-groups.json`;
it is not sent to models or added to frozen experiment settings.

## Model size and resource charts

API participant profiles have an optional **Model size (B parameters)** field.
Enter total parameter count in billions: `7` for 7B, `0.5` for 500M. For MoE models,
use total parameters, not the active subset. This field does not describe file
size, quantization or VRAM, and is never sent as a generation parameter. Leave it
blank when the size is unknown; the arena does not guess from model names.

Competition summaries and workspace performance groups include **Performance vs
resources**, with size, preparation cost and preparation time on the horizontal
axis and score on the vertical axis. Existing round/model/group filters apply.
Cost and duration are averaged per selected strategy conversation, not summed
across repetitions. Missing measurements are excluded from that chart. Preparation
time includes model and tool work and depends on hardware, quantization and
concurrency. Size alone is not a measure of running cost.

Detailed metrics and CSV exports include `model_size_billion`; result exports also
include `score_per_billion` (score from 0 to 1 divided by parameter count in
billions). This ratio complements the raw score; it is not a replacement ranking.
Saved model sizes take precedence. For older competitions without a saved size,
the interface and CSV export can use the current profile only when its ID,
provider, exact model ID and endpoint match. Existing competition files are not
rewritten. Frozen strategy exports preserve size in their origin metadata.


### Create directly from a workspace

Use **New competition** in the workspace header (or on its card) to create a
configuration assigned to that workspace. Saved configurations appear under
**Ready to launch** in the workspace, with Edit and Launch actions.
**Add existing competitions** only organizes competitions/configurations you
already have.

The competition editor keeps the model list in a compact scrollable panel with
search and **Selected only**. Filtering does not deselect hidden profiles. The
bottom bar shows the selected count and keeps **Save configuration** accessible
while editing, including on smaller screens. Saving still makes no model calls.

## Parallel preparation

In the competition editor, **Parallel model requests** sets the maximum number
of simultaneous provider requests (1 to 20). The default is **1**, preserving
sequential execution. The setting applies to initial preparation and subsequent
feedback/no-feedback rounds and is frozen when the competition starts.

Each conversation keeps its own source files, tools, history and streamed output.
Only provider transports run in background threads. One coordinator executes
tools and engine fights, writes checkpoints and accounts for shared spending.
A request waits when another active request temporarily holds the required budget
reservation. Models sharing a loopback server and port run one conversation at a
time to avoid loading several local models or repeatedly swapping them in memory.
Hosted requests can overlap up to the selected limit; provider quotas still apply.

Submitted sources remain frozen. Available fights run progressively, and the next
round still waits for all participants. A failed provider retains its place and
can be recovered without regenerating healthy peers. **Stop** stops scheduling
new work and lets already dispatched requests return or time out; received replies
and pending tools are saved for Resume. Killing the process before a receipt is
saved can still require billing reconciliation.

Preparation duration includes request waiting and coordination, not just token
generation. Resource exports record `parallel_requests`, and workspace comparison
groups keep different concurrency settings separate.

## Edit an existing competition

Stop the run, then use **More → Edit participants** to withdraw, reactivate or add
profiles without creating another competition. Completed work stays in place.
Expand **Freeze preparation** to keep a track fighting with its preceding submitted
strategy without further model calls. Freeze and pool changes are audited; already
submitted versions are never regenerated. See [recovery details](recovery.md#change-participants-without-restarting).

The **Errors** tab filters observed failures by model, round and track. It includes
failed compilation checks, unknown tools, invalid arguments, team validation,
runtime errors and separate provider failures, with rates, recent incidents and an
**errors.csv** export. These observations are not an automatic hallucination score.

## Tool-call comparisons and live activity

The competition overview shows **Total tool calls** and **Performance vs resources**,
with **Tool calls** selected by default. The total is the sum of tool invocations
in the selected rounds/models. The performance chart uses mean invocations per
strategy, so repetitions do not inflate its horizontal axis. Every tool in a batch
counts separately; failed invocations count too. Message and API-response counts
are retained in logs/exports but do not determine these charts. References are
excluded. Workspace comparison groups expose the same tool totals and means;
workspace resource tables show tool calls instead of message counts.

An activity panel is present on every competition tab. It refreshes independently
of the detailed **Live** toggle, showing the current round, active participants,
submitted/validated strategies, tournament progress, models awaiting responses,
and the engine's current pair or compilation. Preparation tests and reference
checks are labelled separately from tournament fights. Durations, last recorded
progress and the most recent activity observation are visible. When available,
provider stream-file updates are reported without loading the streamed text.

Resume also reports checkpoint verification instead of appearing idle while it
checks source and journal integrity. Stopped jobs suppress stale engine/request
markers. Withdrawn profiles remain archived, but no longer inflate active
participant counts in the competition list, configuration or progress panel.
