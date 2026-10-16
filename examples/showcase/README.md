# Weapons, chips and summons example

From the repository root, after the normal installation:

```sh
python -m arena tournament examples/showcase/tournament.json --out runs/feature-showcase
python -m arena ui --open
```

Use the activated virtual environment, or replace `python` with `.venv/bin/python`
on Linux/macOS and `.venv\Scripts\python.exe` on Windows. Choose a new output
folder when rerunning changed sources. Open this competition in Matches to inspect
the replay, raw events, statistics and sources.

The scenario runs two matches with reversed sides and seed 101. Each side has two
level-100 leeks with valid capital allocations. The showcase alternates pistol
and machine gun, attacks with shock, heals with bandage, applies helmet and
protein, moves and summons a puny bulb. The bulb has its own callback and turns,
heals allies and attacks with pebble. The predictable opponent deals damage so
healing can be observed. Debug messages explain successful actions.

This is a mechanics demonstration, not an optimized strategy or an exhaustive
check of every item and effect. It makes no model/API calls. Summons appear after
creation in the schematic replay, as square markers with their own health cards.
Official animations and some effects are not reproduced; raw events are the reference.
