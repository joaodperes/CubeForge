# CubeForge — KeyForge Cube Drafting

CubeForge is an unofficial KeyForge draft simulator with AI opponents, a graphical
draft interface, per-copy randomized enhancements, and post-draft deckbuilding.

## Rules

- Each player drafts six packs of ten cards (60 total picks).
- Build a **36-card deck** with **exactly three houses**, twelve cards per house.
- To include a house, select at least six drafted cards from that house.
- Any remaining slots in that house are filled with its designated token.
- Other KeyForge Alliance deckbuilding restrictions still apply.

| House | Filler token |
| --- | --- |
| Brobnar | Warrior |
| Dis | Snare |
| Logos | Chronicler |
| Mars | Rebel |
| Sanctum | Defender |
| Shadows | Prowler |
| Untamed | Twilight Pixie |

This is an experimental fan-made drafting variant, not official KeyForge rules.

## Quick start

Requires Python 3.10+ with Tkinter available on your system.

```sh
pip install -r requirements.txt
python cubeforge.py
```

The launcher automatically prepares the full cube, opens the graphical draft,
and configures bot opponents. At the end of the draft, you can export all 60
picks (including each copy's enhancements) or choose **Build 36-Card Deck**.

### Select a preset

```sh
# Main cube: seven houses, 580 draftable copies (supports up to 9 players)
python cubeforge.py --preset full --players 3

# Three-card fixture: Adaptoid, Rowdy Skald, Vapor Imp (up to 4 players)
python cubeforge.py --preset enhancement-test --players 3 --seed 42

# Repeatable full-cube draft without enhancements
python cubeforge.py --preset full --seed 42 --no-enhancements

# Generate and check files without opening the desktop GUI
python cubeforge.py --preset enhancement-test --prepare-only
```

The enhancement-test preset intentionally includes three card titles, each
repeated 96 times. **It is for testing enhancements, not the complete cube.**
The original three-card test list remains in `cards/cards.txt` and has also
been saved as `presets/enhancement-test.txt`. The original full cube is in
`presets/full.txt`.

### Custom cubes

Create a plain-text file with one desired card name per line. Repeated names
represent multiple copies:

```sh
python cubeforge.py --preset custom --card-list my_cube.txt --players 3
```

The generator resolves unambiguous differences in punctuation, accents and
capitalization between your card list and DoK metadata. Missing or ambiguous
titles are recorded in the generation log.

### Refresh your card metadata

A `cards/cards.json` database is already included, so the launcher works
offline. To fetch an updated copy from the Decks of KeyForge public API, first
get your own API key, then set the `DOK_API_KEY` environment variable:

```sh
# macOS / Linux:
export DOK_API_KEY="your-api-key"
python cubeforge.py --refresh-cards --prepare-only

# PowerShell:
$env:DOK_API_KEY = "your-api-key"
python cubeforge.py --refresh-cards --prepare-only
```

The key is used in an HTTP header and is never saved in the repository.
The endpoint and the returned schema depend on the external DoK service.
Use `--card-data path/to/cards.json` to work with an alternative metadata
export without replacing the checked-in file.

By default the launcher reuses the images bundled with the repository. Add
`--download-images` to fetch missing artwork. It writes generated cubes,
logs, and drafts locally; it does not commit or push your changes.

## Draft AI

Bots use AERC-like value goals, existing cards' synergies, house commitment,
and the individual enhancement symbols assigned to the copy being drafted.
Each bot pick logs its weighted components. This is a heuristic, not a perfect
KeyForge deck evaluator; balancing the weights through repeatable simulations
is an ongoing task.

Use a numeric `--seed` to reproduce a particular enhancement allocation and
pack shuffle. Different cards with the same name keep separate `CopyId` values.

## Exports

- **Export JSON** saves all 60 drafted picks per player, including houses,
  copy identities, printed Æmber and enhancement counts.
- **Build 36-Card Deck** lets you choose three eligible houses and select
  6–12 cards from each. Filler tokens complete the deck automatically.
- Generated cubes and logs go to `cards/generated/`, which is Git-ignored.

## Development

```sh
python -m unittest discover -s tests -v
python -m py_compile cubeforge.py cube_generator.py draft_simulator.py draft_ui.py
```

The old scripts `cube_generator.py`, `draft_simulator.py`, and `draft_ui.py`
remain available for advanced use. The launcher is the recommended entry point.

## Future work

- More houses, sets, special and linked cards
- Improved bot strategy and full automated draft simulation
- Balance reports for original cards and generated enhancements
- Better scaling and accessibility of the desktop card viewer
