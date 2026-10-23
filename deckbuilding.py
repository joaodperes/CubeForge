"""Pure KeyForge CubeForge deckbuilding and card export helpers."""
TOKEN_NAMES = {
    'Brobnar': 'Warrior',
    'Dis': 'Snare',
    'Logos': 'Chronicler',
    'Mars': 'Rebel',
    'Sanctum': 'Defender',
    'Shadows': 'Prowler',
    'Untamed': 'Twilight Pixie',
}
ENHANCEMENT_KEYS = ('Enh.Amber', 'Enh.Capture', 'Enh.Draw',
                    'Enh.Damage', 'Enh.Discard')


def export_card(card, index):
    """Preserve the card's unique randomized enhancements in saved drafts."""
    if not isinstance(card, dict):
        return {'id': index + 1, 'card': str(card), 'enhancements': {}}
    return {
        'id': index + 1,
        'card': card.get('CardTitle', ''),
        'copy_id': card.get('CopyId', f'legacy-{index + 1}'),
        'house': card.get('House', ''),
        'amber': card.get('Amber', 0),
        'enhancements': {key: card.get(key, 0) for key in ENHANCEMENT_KEYS},
    }


def build_deck(chosen):
    """Build a legal house/token structure from {house: [selected copies]}.

    Exactly 3 houses, with 6–12 non-token cards each. This checks CubeForge's
    house-selection rule, not every optional KeyForge Alliance restriction.
    """
    if len(chosen) != 3:
        raise ValueError('A deck must contain exactly three houses')

    deck = []
    seen = set()
    token_counts = {}
    for house, cards in chosen.items():
        if house not in TOKEN_NAMES:
            raise ValueError(f'Unknown or unsupported token house: {house}')
        if not 6 <= len(cards) <= 12:
            raise ValueError(f'{house} must contribute 6–12 drafted cards, got {len(cards)}')
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError('Each selected card must include its house and copy information')
            if card.get('House') != house:
                raise ValueError(f"Card {card.get('CardTitle')} does not belong to {house}")
            identity = card.get('CopyId')
            if not identity:
                raise ValueError('Selected card is missing CopyId')
            if identity in seen:
                raise ValueError(f'Card copy selected more than once: {identity}')
            seen.add(identity)
            deck.append(export_card(card, len(deck)))
        tokens = 12 - len(cards)
        token_counts[house] = tokens
        for i in range(tokens):
            deck.append({
                'id': len(deck) + 1,
                'card': TOKEN_NAMES[house],
                'house': house,
                'copy_id': f'token:{house}:{i + 1}',
                'amber': 0,
                'enhancements': {},
                'is_token': True,
            })

    if len(deck) != 36:
        raise ValueError('Internal deck error: expected 36 cards')
    return {'houses': list(chosen), 'cards': deck, 'tokens_per_house': token_counts}
