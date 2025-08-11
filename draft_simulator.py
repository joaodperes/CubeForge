import random
import json
import os

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
    if val is None:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        return float(str(val).replace(',', '.'))
    except:
        return 0.0

def safe_int(val, default=0):
    if val is None or val == '':
        return default
    try:
        if isinstance(val, int):
            return val
        return int(float(str(val).replace(',', '.')))
    except:
        return default

def title_for(item):
    """Return the card title whether item is a dict (copy) or a plain string title."""
    if isinstance(item, dict):
        return item.get('CardTitle') or item.get('cardTitle') or ''
    return str(item)

def load_cube_md(md_path):
    """
    Parse the cube.md produced by cube_generator.py.
    Returns list of dicts (one per card copy).
    The parser reads the header row to determine column indices, so column order is flexible.
    """
    if not os.path.exists(md_path):
        raise FileNotFoundError(md_path)

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]

    headers = []
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('|') and '---' not in line:
            # first header-looking line
            # split and strip
            parts = [p.strip() for p in line.strip().split('|')[1:-1]]
            headers = parts
            header_idx = i
            break

    if not headers:
        raise ValueError("Could not find header row in cube.md")

    # Normalise headers (no surrounding spaces)
    headers = [h for h in headers]

    cards = []
    # Data rows start after header and the '---' separator
    for line in lines[header_idx+2:]:
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.strip().split('|')[1:-1]]
        if len(parts) < len(headers):
            # ignore short/invalid rows
            continue
        row = dict(zip(headers, parts))

        # Skip rows that are clearly header repeats
        if row.get(headers[0], '').lower() in ('', '---'):
            continue

        # Extract image link if in markdown [text](path)
        img_link = row.get('Image Link', '') or row.get('Image', '') or ''
        # find parentheses content
        img_path = ''
        if '(' in img_link and ')' in img_link:
            start = img_link.find('(') + 1
            end = img_link.find(')', start)
            img_path = img_link[start:end]
        else:
            img_path = img_link

        # Build card-copy dict and coerce types for known columns
        cc = {
            'House': row.get('House', ''),
            'CardTitle': row.get('CardTitle', row.get('Card', '')),
            'ImageLink': img_path,
            'IsToken': (row.get('Is Token', row.get('IsToken', '')).strip().lower() == 'yes'),
            'AmberControl': parse_float(row.get('AmberControl', row.get('extraCardInfo.amberControl', ''))),
            'ExpectedAmber': parse_float(row.get('ExpectedAmber', row.get('extraCardInfo.expectedAmber', ''))),
            'ArtifactControl': parse_float(row.get('ArtifactControl', row.get('extraCardInfo.artifactControl', ''))),
            'CreatureControl': parse_float(row.get('CreatureControl', row.get('extraCardInfo.creatureControl', ''))),
            'Efficiency': parse_float(row.get('Efficiency', row.get('extraCardInfo.efficiency', ''))),
            'Recursion': parse_float(row.get('Recursion', row.get('extraCardInfo.recursion', ''))),
            'Amber': safe_int(row.get('Amber', row.get('amber', 0)), 0),
            # enhancements — try both header forms e.g. 'Enh.Amber' or 'extraCardInfo.enhancementAmber'
            'Enh.Amber': safe_int(row.get('Enh.Amber', row.get('extraCardInfo.enhancementAmber', 0)), 0),
            'Enh.Capture': safe_int(row.get('Enh.Capture', row.get('extraCardInfo.enhancementCapture', 0)), 0),
            'Enh.Draw': safe_int(row.get('Enh.Draw', row.get('extraCardInfo.enhancementDraw', 0)), 0),
            'Enh.Damage': safe_int(row.get('Enh.Damage', row.get('extraCardInfo.enhancementDamage', 0)), 0),
            'Enh.Discard': safe_int(row.get('Enh.Discard', row.get('extraCardInfo.enhancementDiscard', 0)), 0),
        }
        cards.append(cc)
    return cards

def build_card_pool(cards):
    """
    cards: list of per-copy dicts returned by load_cube_md.
    Return a pool list of card-copy dicts and a secondary empty dict for compatibility.
    """
    pool = []
    for c in cards:
        if c.get('IsToken'):
            continue
        pool.append(c)
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

        house_list = entry.get('houses', []) or entry.get('house', [])
        house = house_list[0] if isinstance(house_list, list) and house_list else (house_list if isinstance(house_list, str) else None)

        # Try to read extraCardInfo fields; JSON may contain dotted keys or nested object.
        def gf(key, default=0):
            # dotted literal
            if key in entry and entry[key] not in (None, ''):
                return entry[key]
            # nested lookups
            extra = entry.get('extraCardInfo', {}) or {}
            if key in extra:
                return extra[key]
            # dotted literal alternative:
            dotted = f"extraCardInfo.{key}"
            if dotted in entry:
                return entry[dotted]
            return default

        # traits and synergies handling: tolerate dotted-key style too
        traits = entry.get('extraCardInfo.traits', entry.get('traits', [])) or []
        synergies = entry.get('extraCardInfo.synergies', entry.get('synergies', [])) or []

        stats[title] = {
            'amberControl': float(gf('amberControl', 0.0)),
            'expectedAmber': float(gf('expectedAmber', 0.0)),
            'artifactControl': float(gf('artifactControl', 0.0)),
            'creatureControl': float(gf('creatureControl', 0.0)),
            'efficiency': float(gf('efficiency', 0.0)),
            'recursion': float(gf('recursion', 0.0)),
            'traits': traits,
            'synergies': synergies,
            # keep comboWith if present
            'comboWith': entry.get('comboWith', []),
            'house': house
        }

        if house:
            house_map[title] = house

    return stats, house_map

def bot_pick(pack, picked_cards, stats, house_map, bot_index):
    """
    pack: list of items which may be dicts (card-copy) or strings (title).
    picked_cards: list of previously picked items (same representation as stored in players lists).
    """
    best_score = None
    best_card = None

    # helpers to get title and card_stats
    def title_of(item):
        return title_for(item)

    # Build house counts and picked traits by looking up titles in stats/house_map
    house_counts = {}
    picked_traits = set()
    picked_cards_set = set(title_of(pc) for pc in picked_cards)

    for c in picked_cards:
        t = title_of(c)
        h = house_map.get(t)
        if h:
            house_counts[h] = house_counts.get(h, 0) + 1
        card_stats = stats.get(t, {})
        for trait in card_stats.get('traits', []):
            tt = trait.get('trait') if isinstance(trait, dict) else trait
            if tt:
                picked_traits.add(tt)

    # Current stat totals
    current_stats = {k: 0.0 for k in TARGET_STATS}
    for c in picked_cards:
        ctitle = title_of(c)
        c_stats = stats.get(ctitle, {})
        for k in TARGET_STATS:
            current_stats[k] += c_stats.get(k, 0.0)

    distinct_houses = len(house_counts)

    # Evaluate each candidate in pack
    for candidate in pack:
        ctitle = title_of(candidate)
        card_stats = stats.get(ctitle, {})
        house = house_map.get(ctitle)
        if not card_stats or not house:
            continue

        ### --- Trait Synergy Score ---
        synergy_score = 0.0
        for synergy in card_stats.get('synergies', []):
            trait = synergy.get('trait')
            rating = synergy.get('rating', 0)
            house_condition = synergy.get('house', 'anyHouse')
            if trait in picked_traits:
                valid = (
                    house_condition == 'anyHouse' or
                    (house_condition == 'house' and house == house_map.get(ctitle)) or
                    (house_condition == 'outOfHouse' and house != house_map.get(ctitle))
                )
                if valid:
                    synergy_score += rating * 1.0

        ### --- Direct Combo Score ---
        combo_bonus = 0.0
        for combo_card in card_stats.get('comboWith', []):
            if combo_card in picked_cards_set:
                combo_info = stats.get(combo_card, {})
                house_condition = combo_info.get('house', 'anyHouse')
                valid = (
                    house_condition == 'anyHouse' or
                    (house_condition == 'house' and house == house_map.get(combo_card)) or
                    (house_condition == 'outOfHouse' and house != house_map.get(combo_card))
                )
                if valid:
                    combo_bonus += 2.0

        ### --- Potential Future Combo Score ---
        future_combo_bonus = 0.0
        for picked in picked_cards:
            picked_stats = stats.get(title_of(picked), {})
            for target in picked_stats.get('comboWith', []):
                if target == ctitle:
                    house_condition = picked_stats.get('house', 'anyHouse')
                    valid = (
                        house_condition == 'anyHouse' or
                        (house_condition == 'house' and house == house_map.get(title_of(picked))) or
                        (house_condition == 'outOfHouse' and house != house_map.get(title_of(picked)))
                    )
                    if valid:
                        future_combo_bonus += 1.0

        ### --- House Commitment Multiplier ---
        house_count = house_counts.get(house, 0)
        if distinct_houses < 3:
            house_multiplier = 1.0
        elif house in house_counts:
            if house_count > 12:
                house_multiplier = 1 / (1.2 ** (house_count - 12))
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
            house_multiplier = 0.5

        ### --- Stat-Based Score ---
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

        total_score = (synergy_score + combo_bonus + future_combo_bonus) * house_multiplier + stat_score

        if best_score is None or total_score > best_score:
            best_score = total_score
            best_card = candidate

    chosen_card = best_card or random.choice(pack)
    # log the pick
    get_bot_logs()[bot_index].append({
        "pick_num": len(picked_cards) + 1,
        "pack": [title_for(x) for x in pack],
        "picked_cards": [title_for(x) for x in picked_cards],
        "chosen_card": title_for(chosen_card),
        "score": best_score,
        "house_counts": dict(house_counts),
        "current_stats": current_stats,
    })
    return chosen_card

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
                    pick = random.choice(pack)
                    pack.remove(pick)
                    players[i].append(pick)
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
            title = title_for(card)
            house = house_map.get(title, 'Unknown')
            house_counts[house] = house_counts.get(house, 0) + 1
            print(f"[{house}] {title}")
        print(f"Houses used: {house_counts}")

if __name__ == '__main__':
    try:
        cards = load_cube_md(CUBE_MD_PATH)
        card_pool, _ = build_card_pool(cards)
        stats, house_map = load_card_stats_from_json(CARDS_JSON_PATH)

        num_players = input(f"Enter number of players (default {DEFAULT_NUM_PLAYERS}): ").strip()
        num_players = int(num_players) if num_players else DEFAULT_NUM_PLAYERS

        initialize_bot_logs(num_players)
        players = run_draft(card_pool, house_map, stats, num_players)
        display_drafts(players, house_map)

        with open("bot_logs.json", "w", encoding="utf-8") as f:
            json.dump(_BOT_LOGS, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Error: {e}")