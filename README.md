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
| Brobnar | Warrior | ![Warrior](/cards/Brobnar/warrior.png) |
| Dis | Snare | ![Snare](/cards/Dis/Snare.png)|
| Logos | Chronicler | ![Chronicler](/cards/Logos/Chronicler.png) |
| Mars | Rebel | ![Rebel](/cards/Mars/Rebel.png) |
| Sanctum | Defender | ![Defender](/cards/Sanctum/Defender.png) |
| Shadows | Prowler | ![Prowler](/cards/Shadows/Prowler.png) |
| Untamed | Twilight Pixie | ![Twilight Pixie](/cards/Untamed/Twilight_Pixie.png)|

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