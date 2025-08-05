import random
import json

# Configuration
PACK_SIZE = 10
NUM_ROUNDS = 6
DEFAULT_NUM_PLAYERS = 3
CUBE_MD_PATH = 'cards/cube.md'
CARDS_JSON_PATH = 'cards/cards.json'

# Draft goals (used for evaluating picks)
TARGET_STATS = {
    "amberControl": 10,
    "expectedAmber": 18,
    "artifactControl": 1,
    "creatureControl": 12
}

def parse_float(val):
    try:
        return float(val.replace(',', '.'))
    except:
        return 0.0

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
                    continue
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

def build_card_pool(cards):
    pool = []
    for card in cards:
        pool.extend([card['CardTitle']] * card['NrCopies'])
    return pool, {}

def load_card_stats_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {}
    house_map = {}

    for entry in data:
        title = entry.get('cardTitle')
        if not title:
            continue

        house_list = entry.get('houses', [])
        house = house_list[0] if house_list else None

        extra = entry
        traits = extra.get("extraCardInfo.traits", [])
        synergies = extra.get("extraCardInfo.synergies", [])

        stats[title] = {
            'amberControl': extra.get('extraCardInfo.amberControl', 0.0),
            'expectedAmber': extra.get('extraCardInfo.expectedAmber', 0.0),
            'artifactControl': extra.get('extraCardInfo.artifactControl', 0.0),
            'creatureControl': extra.get('extraCardInfo.creatureControl', 0.0),
            'efficiency': extra.get('extraCardInfo.efficiency', 0.0),
            'recursion': extra.get('extraCardInfo.recursion', 0.0),
            'traits': traits,
            'synergies': synergies
        }

        if house:
            house_map[title] = house

    return stats, house_map

def bot_pick(pack, picked_cards, stats, house_map):
    best_score = None
    best_card = None
    house_counts = {}
    picked_traits = set()

    # Step 1: Collect picked traits and house counts
    for c in picked_cards:
        h = house_map.get(c)
        if h:
            house_counts[h] = house_counts.get(h, 0) + 1
        card_stats = stats.get(c, {})
        for trait in card_stats.get('traits', []):
            t = trait.get('trait')
            if t:
                picked_traits.add(t)

    # Step 2: Evaluate all cards in the pack
    for card in pack:
        card_stats = stats.get(card, {})
        house = house_map.get(card)
        if not card_stats or not house:
            continue

        ### --- 1. Trait/Synergy-Based Scoring (Primary) ---
        synergy_score = 0.0
        for synergy in card_stats.get('synergies', []):
            trait = synergy.get('trait')
            rating = synergy.get('rating', 0)
            if trait in picked_traits:
                synergy_score += rating * 1.0  # ← BIG impact now

        ### --- 2. House Commitment Scoring (Secondary) ---
        house_count = house_counts.get(house, 0)
        if house_count > 12:
            house_multiplier = 1 / (1.2 ** (house_count - 12))  # soften exponential
        elif house_count == 12:
            house_multiplier = 1.75
        elif 9 <= house_count < 12:
            house_multiplier = 1.5
        elif 6 <= house_count < 9:
            house_multiplier = 1.3
        elif 3 <= house_count < 6:
            house_multiplier = 1.1
        elif 1 <= house_count < 3:
            house_multiplier = 0.9
        else:
            house_multiplier = 0.75

        ### --- 3. Card Stat Score (Tie-breaker) ---
        stat_score = (
            0.1 * sum(card_stats.get(k, 0) * TARGET_STATS.get(k, 0) for k in TARGET_STATS)
            + 0.05 * card_stats.get('efficiency', 0)
            + 0.05 * card_stats.get('recursion', 0)
        )

        ### --- Final Score ---
        total_score = synergy_score * house_multiplier + stat_score

        if best_score is None or total_score > best_score:
            best_score = total_score
            best_card = card

    return best_card or random.choice(pack)

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

def display_drafts(players, house_map):
    for i, picks in enumerate(players):
        print(f"=== Player {i+1} Picks ===")
        house_counts = {}
        for card in picks:
            house = house_map.get(card, 'Unknown')
            house_counts[house] = house_counts.get(house, 0) + 1
            print(f"[{house}] {card}")
        print(f"Houses used: {house_counts}")

if __name__ == '__main__':
    try:
        cards = load_cube_md(CUBE_MD_PATH)
        card_pool, _ = build_card_pool(cards)
        stats, house_map = load_card_stats_from_json(CARDS_JSON_PATH)

        num_players = input(f"Enter number of players (default {DEFAULT_NUM_PLAYERS}): ").strip()
        num_players = int(num_players) if num_players else DEFAULT_NUM_PLAYERS

        players = run_draft(card_pool, house_map, stats, num_players)
        display_drafts(players, house_map)

    except Exception as e:
        print(f"Error: {e}")