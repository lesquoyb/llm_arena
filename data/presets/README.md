# Fixed scenario data

`dream-team.json` stores the frozen public Dream team, not a network query.
The fetcher reads the current first farmer in the public active talent ranking,
then four public leeks belonging to that farmer. It never fixes the farmer ID.

Populate once with `python scripts/import_dream_team.py --save-preset`, then
commit the resulting file. Selecting the preset needs no network. An explicit
manual UI refresh writes a local override without modifying previous competitions.

The current status records missing real data because cloud access returns
HTTP 403. No fictional stats or builds are substituted. The four IDs supplied
by the user are an observation of the current leader, not a permanent selection.
