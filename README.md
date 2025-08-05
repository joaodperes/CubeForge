# CubeForge: A Keyforge Cube!

## Intro

CubeForge aims to create a draft mode in Keyforge.
To support this, the _current_ ruleset is as follows:

1.  6 packs of 10 cards per player (300 cards supports 60 * 5 players)
2.  Alliance deck building rules still apply
3.  To add a house to your deck, you must have at least 6 cards from that house. The rest of the house will be filled with the house token in question (see below)

The full card list can be found in the [cards](/cards/) folder, and the card images in each house's subfolder.

## Token Table

When a house in your deck has less than 12 cards (but at least 6), you must fill it up to 12 with that house's associated token.

| House | Token Name | Token Image |
|-------|------------|-------------|
| ![Brobnar](https://decksofkeyforge.com/static/media/brobnar.c40aaae2e299334c1554.png) | Warrior | ![Warrior](/cards/Brobnar/warrior.png) |
| ![Dis](https://decksofkeyforge.com/static/media/dis.35644fd3bf6c380d0642.png) | Snare | ![Snare](/cards/Dis/Snare.png)|
| ![Logos](https://decksofkeyforge.com/static/media/dis.35644fd3bf6c380d0642.png) | Chronicler | ![Chronicler](/cards/Logos/Chronicler.png) |
| ![Mars](https://decksofkeyforge.com/static/media/mars.7859071a456f03742a2a.png) | Rebel | ![Rebel](/cards/Mars/Rebel.png) |
| ![Sanctum](https://decksofkeyforge.com/static/media/sanctum.5aa2df51e8a124c596bf.png) | Defender | ![Defender](/cards/Sanctum/Defender.png) |
| ![Shadows](https://decksofkeyforge.com/static/media/shadows.ba312e6bbde412ebb397.png) | Prowler | ![Prowler](/cards/Shadows/Prowler.png) |
| ![Untamed](https://decksofkeyforge.com/static/media/untamed.7db4a2fb00228c9162f7.png) | Twilight Pixie | ![Twilight Pixie](/cards/Untamed/Twilight_Pixie.png)|

## Future Ideas

- [ ] Add more houses
- [ ] Extend the cardpool beyond CoTA and AoA
- [ ] Add enhancements
- [ ] Add house enhancements
- [ ] Add Gigantics
- [ ] Add Special rarity / linked cards

# Custom Cube

A custom cube can be created via cube_generator.py.

Start by running ```pip install -r requirements.txt``` in the terminal, then add ```cards.json``` to the [/cards/](/cards/) folder. You can get it using, for instance, the [Decks of Keyforge](https://decksofkeyforge.com/) API through a script. If you're unsure how to do this, feel free to use cards.py in my [Decks-of-Keyforge repo](https://github.com/joaodperes/Decks-of-Keyforge).

```cards.txt``` is the list of cards to add to the cube, one per line of text. 

> [!IMPORTANT] 
> cards.json file will not include special characters in the cardTitle value, so some transformations may be required:
> ```Po's Pixies -> Pos Pixies```

To run the script, just open the terminal and type ```python cube_generator.py```.

# Draft Simulator

Using draft_simulator.py you can simulate a draft with at least 2 bots. The maximum supported number of bots will be determined by the number of cards available in the cube; currently it is 9 players (1 human + 8 bots) as 10 would require 600 cards, excluding tokens.

> [!IMPORTANT] 
> For a visual draft, use ```python draft_ui.py``` instead

The draft does not include tokens in the pool and the bots have the following draft goals:

- AERC value goals (defined in ```TARGET_STATS```)
- Drafting full houses (12 cards)
- When a full house has already been drafted, it can still pick cards in that house when the score is significantly higher than the worst card's in that house
- While not strictly a goal, Efficiency and Recursion values also increase the card's score

> [!NOTE]
> Synergies, traits and other bonuses are currently not assessed

To simulate a draft, run ```python draft_simulator.py```. You'll be given 10 numbered cards, pick one and move to the next pack, until all 6 rounds have been drafted!