# Round context and source access

Each improvement round starts a fresh conversation. Previous assistant messages,
reasoning and tool results are not resent. The previous frozen submission
(including team.json when present) is copied into the workspace before any model
call. `previous_submission` identifies its round, entrypoint and files and gives
explicit read calls. Reading a file is still the model's responsibility.

With feedback, the phase instruction gives the current round and configured
maximum, then a win/draw/loss/failure summary and score for each earlier round of
that trajectory. Tournament opponents can change, so those scores are descriptive,
not a comparison against a constant panel. Without feedback, the instruction
gives phase and source context but no past results.

## Pulling earlier records

- `list_submissions {}` lists all own earlier frozen versions by round.
- `read_submitted_file {"round": 1, "path": "main.leek"}` reads a frozen file.
  The file is verified against its archived submission before being returned.
- `list_past_fights {}` lists previous-round tournament fights.
- `list_past_fights {"round": 1}` selects an older round from `available_rounds`.
- `read_past_fight {"fight_id": "...", "section": "overview"}` identifies the
  round and own frozen submission, including its files and a source read call.
  Other sections are `actions`, `turns` and `logs`.

For text pages, follow the returned continuation until `next_offset` is null.
Source tools are available in both tracks. Past-fight tools are refused by the
server without feedback access, including manually forged calls. Access stays
within the same model, replicate and ancestor chain: initial source plus earlier
versions of the current track. Other tracks, opponent scripts, opponent debug
logs and future fights remain inaccessible. Mirrors and reference evaluations
are excluded from competition feedback.

Calibration has the same round/source association, but past-fight tools expose
training and previous-version tests only. Validation and audit results are not
available to the target or analyst. Tools disabled by the calibration candidate
remain disabled even if mentioned in documentation.

## Inspecting inherited files in the interface

For a fresh-round conversation, Code & versions starts with the verified files
inherited from the previous submission. Later writes are compared against that
baseline. Inherited files have no corresponding message in the new conversation.
This also works when inspecting existing fresh-round archives. New phase text
is generated for newly created rounds; already recorded prompts are unchanged.
