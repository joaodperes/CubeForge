import csv
import random

# Configuration
PACK_SIZE = 10
NUM_ROUNDS = 6
DEFAULT_NUM_PLAYERS = 3
CUBE_MD_PATH = 'cards/cube.md'
STATS_CSV_PATH = 'cards/cube_stats.csv'

# Draft goals (used for evaluating picks)
TARGET_STATS = {
    "amberControl": 10,
    "expectedAmber": 18,
    "artifactControl": 1,
    "creatureControl": 12
}

# Parse float helper
def parse_float(val):
    try:
        return float(val.replace(',', '.'))
    except:
        return 0.0

# Load card data from cube.md, skipping tokens
def load_cube_md(md_path):
    cards = []
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('|') and 'CardTitle' not in line:
                parts = [p.strip() for p in line.strip().split('|')[1:-1]]
                if len(parts) < 5:
                    continue
                house = parts[0]
                card_title = parts[1]
                if not card_title or card_title == '---':
                    continue  # skip invalid rows
                try:
                    nr_copies = int(parts[2])
                except ValueError:
                    nr_copies = 1
                is_token = parts[-1] == 'Yes'
                if not is_token:
                    cards.append({
                        'House': house,
                        'CardTitle': card_title,
                        'NrCopies': nr_copies
                    })
    return cards

# Load card stats from CSV (names aligned to script 1)
def load_card_stats(path):
    stats = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            title = row['CardTitle']
            try:
                stats[title] = {
                    'amberControl': parse_float(row.get('amberControl', 0)),
                    'expectedAmber': parse_float(row.get('expectedAmber', 0)),
                    'artifactControl': parse_float(row.get('artifactControl', 0)),
                    'creatureControl': parse_float(row.get('creatureControl', 0)),
                    'efficiency': parse_float(row.get('efficiency', 0)),
                    'recursion': parse_float(row.get('recursion', 0))
                }
            except:
                continue
    return stats

# Build card pool and house map
def build_card_pool(cards):
    pool = []
    house_map = {}
    for card in cards:
        pool.extend([card['CardTitle']] * card['NrCopies'])
        house_map[card['CardTitle']] = card['House']
    return pool, house_map

# Bot pick logic with soft house disincentive
def bot_pick(pack, picked_cards, stats, house_map):
    best_score = None
    best_card = None
    house_counts = {}

    for c in picked_cards:
        h = house_map.get(c)
        house_counts[h] = house_counts.get(h, 0) + 1

    for card in pack:
        house = house_map.get(card)
        s = stats.get(card, None)
        if not house or not s:
            continue

        # Base score from stats
        score = sum(s.get(k, 0) * TARGET_STATS[k] for k in TARGET_STATS)
        score += 0.5 * s.get('efficiency', 0) + 0.5 * s.get('recursion', 0)

        # Get how many cards from this house the player has already drafted
        count = house_counts.get(house, 0)

        # Scoring adjustments to encourage full house commitment
        if count > 12:
            score /= (1.3 ** (count - 12))  # exponential penalty
        elif count == 12:
            score *= 1.5  # perfect house bonus
        elif 9 <= count < 12:
            score *= 1.3
        elif 6 <= count < 9:
            score *= 1.1
        elif 3 <= count < 6:
            score *= 0.95
        elif 1 <= count < 3:
            score *= 0.9

        if best_score is None or score > best_score:
            best_score = score
            best_card = card

    return best_card or random.choice(pack)

# Run the draft
def run_draft(card_pool, house_map, stats, num_players):
    total_packs = num_players * NUM_ROUNDS
    if len(card_pool) < total_packs * PACK_SIZE:
        raise ValueError("Not enough cards to run full draft.")

    random.shuffle(card_pool)
    packs = [[card_pool.pop() for _ in range(PACK_SIZE)] for _ in range(total_packs)]
    players = [[] for _ in range(num_players)]

    for round_index in range(NUM_ROUNDS):
        round_packs = [packs[round_index * num_players + i] for i in range(num_players)]
        direction = 1 if round_index % 2 == 0 else -1

        for pick_num in range(PACK_SIZE):
            for i in range(num_players):
                current_index = (i + pick_num * direction) % num_players
                pack = round_packs[current_index]

                if i == 0:
                    print(f"--- Your pack (Pick {pick_num+1}, Round {round_index+1}) ---")
                    for idx, card in enumerate(pack):
                        print(f"{idx+1}: [{house_map.get(card)}] {card}")
                    while True:
                        try:
                            choice = int(input("Pick a card (1-{}): ".format(len(pack)))) - 1
                            if 0 <= choice < len(pack):
                                pick = pack.pop(choice)
                                players[i].append(pick)
                                break
                        except:
                            pass
                else:
                    pick = bot_pick(pack, players[i], stats, house_map)
                    pack.remove(pick)
                    players[i].append(pick)

    return players

# Display drafted decks with house summary
def display_drafts(players, house_map):
    for i, picks in enumerate(players):
        print(f"=== Player {i+1} Picks ===")
        house_counts = {}
        for card in picks:
            house = house_map.get(card, 'Unknown')
            house_counts[house] = house_counts.get(house, 0) + 1
            print(f"[{house}] {card}")
        print(f"Houses used: {house_counts}")

# Main
if __name__ == '__main__':
    try:
        cards = load_cube_md(CUBE_MD_PATH)
        card_pool, house_map = build_card_pool(cards)
        stats = load_card_stats(STATS_CSV_PATH)

        num_players = input(f"Enter number of players (default {DEFAULT_NUM_PLAYERS}): ").strip()
        num_players = int(num_players) if num_players else DEFAULT_NUM_PLAYERS

        players = run_draft(card_pool, house_map, stats, num_players)
        display_drafts(players, house_map)

    except Exception as e:
        print(f"Error: {e}")