import random
import json
import os

# Configuration
PACK_SIZE = 10
NUM_ROUNDS = 6
DEFAULT_NUM_PLAYERS = 3
CUBE_MD_PATH = os.environ.get('CUBEFORGE_CUBE_PATH', 'cards/cube.md')
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
            'CopyId': row.get('CopyId', f'legacy-{len(cards) + 1}'),
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
            'amberControl': parse_float(gf('amberControl', 0.0)),
            'expectedAmber': parse_float(gf('expectedAmber', 0.0)),
            'artifactControl': parse_float(gf('artifactControl', 0.0)),
            'creatureControl': parse_float(gf('creatureControl', 0.0)),
            'efficiency': parse_float(gf('efficiency', 0.0)),
            'recursion': parse_float(gf('recursion', 0.0)),
            'traits': traits,
            'synergies': synergies,
            # keep comboWith if present
            'comboWith': entry.get('comboWith', []),
            'house': house
        }

        if house:
            house_map[title] = house

    return stats, house_map

def enhancement_score(candidate, current_stats=None):
    """Marginal value of enhancements on this specific physical card copy.

    These are heuristic weights for drafting, not official AERC values.
    Printed amber is already reflected in the normal card statistics.
    """
    if not isinstance(candidate, dict):
        return 0.0
    current_stats = current_stats or {}
    want_amber = current_stats.get('amberControl', 0) < TARGET_STATS['amberControl']
    want_control = current_stats.get('creatureControl', 0) < TARGET_STATS['creatureControl']
    weights = {
        'Enh.Amber': 0.90,
        'Enh.Capture': 0.48 if want_amber else 0.30,
        'Enh.Draw': 0.65,
        'Enh.Damage': 0.50 if want_control else 0.32,
        'Enh.Discard': 0.55
    }
    return sum(weights[key] * max(0, safe_int(candidate.get(key, 0)))
               for key in weights)


def bot_pick(pack, picked_cards, stats, house_map, bot_index):
    """Choose a card by card value, its unique enhancements, combos and house needs."""
    if not pack:
        raise ValueError('Cannot pick from an empty pack')

    house_counts = {}
    picked_trait_houses = {}
    picked_titles = set()
    for picked in picked_cards:
        title = title_for(picked)
        picked_titles.add(title)
        house = (picked.get('House') if isinstance(picked, dict) else None) or house_map.get(title)
        if house:
            house_counts[house] = house_counts.get(house, 0) + 1
        for item in stats.get(title, {}).get('traits', []):
            trait = item.get('trait') if isinstance(item, dict) else item
            if trait:
                picked_trait_houses.setdefault(trait, set()).add(house)

    # Estimate final-deck contributions: ignore cards beyond the first twelve per house.
    current_stats = {key: 0.0 for key in TARGET_STATS}
    used = {}
    top_houses = sorted(house_counts, key=house_counts.get, reverse=True)[:3]
    for picked in picked_cards:
        title = title_for(picked)
        house = (picked.get('House') if isinstance(picked, dict) else None) or house_map.get(title)
        if house not in top_houses or used.get(house, 0) >= 12:
            continue
        used[house] = used.get(house, 0) + 1
        for key in TARGET_STATS:
            current_stats[key] += parse_float(stats.get(title, {}).get(key, 0))

    candidates = []
    for candidate in pack:
        title = title_for(candidate)
        profile = stats.get(title, {})
        house = (candidate.get('House') if isinstance(candidate, dict) else None) or house_map.get(title)
        if not profile or not house:
            candidates.append((float('-inf'), candidate, {}))
            continue

        synergy = 0.0
        for item in profile.get('synergies', []):
            if not isinstance(item, dict):
                continue
            trait = item.get('trait')
            related_houses = picked_trait_houses.get(trait, set())
            condition = item.get('house', 'anyHouse')
            if condition == 'house':
                matches = house in related_houses
            elif condition == 'outOfHouse':
                matches = any(other != house for other in related_houses)
            else:
                matches = bool(related_houses)
            if matches:
                synergy += parse_float(item.get('rating', 0))

        combos = 0.0
        for item in profile.get('comboWith', []):
            combo_title = item.get('cardTitle', item.get('title', '')) if isinstance(item, dict) else item
            if combo_title in picked_titles:
                combos += 2.0
        for selected in picked_cards:
            selected_title = title_for(selected)
            for item in stats.get(selected_title, {}).get('comboWith', []):
                combo_title = item.get('cardTitle', item.get('title', '')) if isinstance(item, dict) else item
                if combo_title == title:
                    combos += 1.0

        # A draft comprises 60 picks but the finished KeyForge deck uses three houses
        # of twelve cards. A fourth house or a thirteenth card should be harder to justify.
        count = house_counts.get(house, 0)
        if count >= 12:
            house_weight = 0.35
        elif house in top_houses:
            house_weight = 1.0 + min(count, 11) * 0.045
        elif len(top_houses) >= 3:
            house_weight = 0.25
        else:
            house_weight = 1.0

        stat_value = 0.0
        for key, goal in TARGET_STATS.items():
            shortfall = max(0.0, goal - current_stats[key])
            if shortfall:
                stat_value += 0.1 * shortfall * parse_float(profile.get(key, 0))
        stat_value += 0.10 * parse_float(profile.get('efficiency', 0))
        stat_value += 0.08 * parse_float(profile.get('recursion', 0))

        enhancements = enhancement_score(candidate, current_stats)
        total = (stat_value + synergy + combos + enhancements) * house_weight
        candidates.append((total, candidate, {
            'base': round(stat_value, 3),
            'synergies': round(synergy, 3),
            'combos': round(combos, 3),
            'enhancements': round(enhancements, 3),
            'house_weight': round(house_weight, 3),
        }))

    best_score, chosen, details = max(candidates, key=lambda row: row[0])
    if best_score == float('-inf'):
        chosen = random.choice(pack)
        best_score, details = None, {}

    get_bot_logs()[bot_index].append({
        'pick_num': len(picked_cards) + 1,
        'pack': [title_for(card) for card in pack],
        'picked_cards': [title_for(card) for card in picked_cards],
        'chosen_card': title_for(chosen),
        'copy_id': chosen.get('CopyId') if isinstance(chosen, dict) else None,
        'score': best_score,
        'score_breakdown': details,
        'house_counts': house_counts,
        'current_stats': current_stats,
    })
    return chosen


def run_draft(card_pool, house_map, stats, num_players):
    if not _BOT_LOGS or len(_BOT_LOGS) != num_players:
        initialize_bot_logs(num_players)
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