import random
import json

# Configuration
PACK_SIZE = 10
NUM_ROUNDS = 6
DEFAULT_NUM_PLAYERS = 3
CUBE_MD_PATH = 'cards/cube.md'
CARDS_JSON_PATH = 'cards/cards.json'
_BOT_LOGS = []

def initialize_bot_logs(num_players):
    global _BOT_LOGS
    _BOT_LOGS = [[] for _ in range(num_players)]

def get_bot_logs():
    if not _BOT_LOGS:
        raise RuntimeError("BOT_LOGS not initialized.")
    return _BOT_LOGS

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

def bot_pick(pack, picked_cards, stats, house_map, bot_index):
    best_score = None
    best_card = None
    house_counts = {}
    picked_traits = set()
    picked_cards_set = set(picked_cards)

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

    # Step 2: Calculate current stat totals
    current_stats = {k: 0.0 for k in TARGET_STATS}
    for c in picked_cards:
        c_stats = stats.get(c, {})
        for k in TARGET_STATS:
            current_stats[k] += c_stats.get(k, 0.0)

    distinct_houses = len(house_counts)

    # Step 3: Evaluate all cards in the pack
    for card in pack:
        card_stats = stats.get(card, {})
        house = house_map.get(card)
        if not card_stats or not house:
            continue

    ### --- 1. Trait Synergy Score ---
    synergy_score = 0.0
    for synergy in card_stats.get('synergies', []):
        trait = synergy.get('trait')
        rating = synergy.get('rating', 0)
        house_condition = synergy.get('house', 'anyHouse')

        if trait in picked_traits:
            valid = (
                house_condition == 'anyHouse' or
                (house_condition == 'house' and house == house_map.get(card)) or
                (house_condition == 'outOfHouse' and house != house_map.get(card))
            )
            if valid:
                synergy_score += rating * 1.0  # Weight stays the same

    ### --- 2. Direct Combo Score ---
    combo_bonus = 0.0
    for combo_card in card_stats.get('comboWith', []):
        if combo_card in picked_cards_set:
            combo_info = stats.get(combo_card, {})
            house_condition = combo_info.get('house', 'anyHouse')  # fallback
            valid = (
                house_condition == 'anyHouse' or
                (house_condition == 'house' and house == house_map.get(combo_card)) or
                (house_condition == 'outOfHouse' and house != house_map.get(combo_card))
            )
            if valid:
                combo_bonus += 2.0  # Still tunable

    ### --- 2b. Potential Future Combo Score ---
    future_combo_bonus = 0.0
    for picked in picked_cards:
        picked_stats = stats.get(picked, {})
        for target in picked_stats.get('comboWith', []):
            if target == card:
                house_condition = picked_stats.get('house', 'anyHouse')
                valid = (
                    house_condition == 'anyHouse' or
                    (house_condition == 'house' and house == house_map.get(picked)) or
                    (house_condition == 'outOfHouse' and house != house_map.get(picked))
                )
                if valid:
                    future_combo_bonus += 1.0

    ### --- 3. House Commitment Multiplier ---
    house_count = house_counts.get(house, 0)
    if distinct_houses < 3:
        house_multiplier = 1.0  # No penalty early on
    elif house in house_counts:
        if house_count > 12:
            house_multiplier = 1 / (1.2 ** (house_count - 12))  # soften exponential
        elif house_count == 11:
            house_multiplier = 1.75
        elif 9 <= house_count < 11:
            house_multiplier = 1.5
        elif 6 <= house_count < 9:
            house_multiplier = 1.3
        elif 3 <= house_count < 6:
            house_multiplier = 1.1
        else:
            house_multiplier = 1.0
    else:
        house_multiplier = 0.5  # Discourage 4th house

    ### --- 4. Stat-Based Score ---
    stat_score = 0.0
    unmet_goals = any(current_stats[k] < TARGET_STATS[k] for k in TARGET_STATS)

    if unmet_goals:
        for k in TARGET_STATS:
            if current_stats[k] < TARGET_STATS[k]:
                stat_score += 0.1 * (TARGET_STATS[k] - current_stats[k]) * card_stats.get(k, 0.0)
    else:
        stat_score += 0.05 * card_stats.get('efficiency', 0.0)
        stat_score += 0.03 * card_stats.get('recursion', 0.0)
        stat_score += 0.02 * card_stats.get('creatureControl', 0.0)

    ### --- 5. Final Score ---
    total_score = (synergy_score + combo_bonus + future_combo_bonus) * house_multiplier + stat_score

    if best_score is None or total_score > best_score:
        best_score = total_score
        best_card = card

    chosen_card = best_card or random.choice(pack)

    ### --- 6. Log the pick ---
    get_bot_logs()[bot_index].append({
        "pick_num": len(picked_cards) + 1,
        "pack": pack.copy(),
        "picked_cards": picked_cards.copy(),
        "chosen_card": chosen_card,
        "score": best_score,
        "house_counts": dict(house_counts),
        "current_stats": current_stats,
        "synergy_score": synergy_score,
        "combo_bonus": combo_bonus,
        "future_combo_bonus": future_combo_bonus,
        "house_multiplier": house_multiplier,
        "stat_score": stat_score,
        "card_house": house,
    })

    return chosen_card or random.choice(pack)

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
                    pick = bot_pick(pack, players[i], stats, house_map, i)
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

        with open("bot_logs.json", "w", encoding="utf-8") as f:
            json.dump(_BOT_LOGS, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Error: {e}")