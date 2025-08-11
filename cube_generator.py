import os
import json
import random
import requests
from collections import Counter, defaultdict

# ----- Config / paths -----
CARDS_DIR = 'cards'
CARDS_TXT = os.path.join(CARDS_DIR, 'cards.txt')
CARDS_JSON = os.path.join(CARDS_DIR, 'cards.json')
OUTPUT_MD = os.path.join(CARDS_DIR, 'cube.md')
LOG_FILE = os.path.join(CARDS_DIR, 'cube.log')

# ----- Enhancement keys & friendly labels -----
ENH_KEYS = [
    ('extraCardInfo.enhancementAmber', 'Enh.Amber'),
    ('extraCardInfo.enhancementCapture', 'Enh.Capture'),
    ('extraCardInfo.enhancementDraw', 'Enh.Draw'),
    ('extraCardInfo.enhancementDamage', 'Enh.Damage'),
    ('extraCardInfo.enhancementDiscard', 'Enh.Discard'),
]

# ----- Helpers -----
def get_field(card, key, default=''):
    # 1) literal key
    if key in card and card[key] not in (None, ''):
        return card[key]

    if '.' in key:
        top, rest = key.split('.', 1)
        # 2) nested form: card[top][rest]
        top_obj = card.get(top)
        if isinstance(top_obj, dict) and rest in top_obj and top_obj[rest] not in (None, ''):
            return top_obj[rest]
        # 3) top-level short name
        if rest in card and card[rest] not in (None, ''):
            return card[rest]
        # 4) explicit extraCardInfo fallback
        extra = card.get('extraCardInfo', {}) or {}
        if rest in extra and extra[rest] not in (None, ''):
            return extra[rest]
    else:
        # not dotted: try top-level then extraCardInfo
        if key in card and card[key] not in (None, ''):
            return card[key]
        extra = card.get('extraCardInfo', {}) or {}
        if key in extra and extra[key] not in (None, ''):
            return extra[key]

    return default

def fmt(value):
    """Formatting similar to previous behavior: replace '.' with ',' for floats"""
    return str(value).replace('.', ',') if isinstance(value, float) else value

def safe_int(val, default=0):
    """Convert value to int safely"""
    if val is None or val == '':
        return default
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return default

# ----- Load titles & counts -----
if not os.path.exists(CARDS_TXT):
    raise SystemExit(f"Missing {CARDS_TXT} - put cards.txt (one title per line) in the '{CARDS_DIR}' folder.")

with open(CARDS_TXT, 'r', encoding='utf-8') as f:
    titles_list = [line.strip() for line in f if line.strip()]
title_counter = Counter(titles_list)

# ----- Load JSON -----
if not os.path.exists(CARDS_JSON):
    raise SystemExit(f"Missing {CARDS_JSON} - put cards.json in the '{CARDS_DIR}' folder.")

with open(CARDS_JSON, 'r', encoding='utf-8') as f:
    cards = json.load(f)

# Map cardTitle -> card (first occurrence)
json_map = {card.get('cardTitle'): card for card in cards if 'cardTitle' in card}

# ----- Logging setup -----
def log_write(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(msg + '\n')

# Start fresh log
with open(LOG_FILE, 'w', encoding='utf-8') as log:
    log.write('=== CUBE GENERATION LOG ===\n')

# Report missing titles
missing = set(title_counter.keys()) - set(json_map.keys())
if missing:
    log_write('Missing JSON entries for these titles:')
    for t in sorted(missing):
        log_write(f" - {t}")
else:
    log_write('All titles found in JSON.')

# ----- Build per-copy pool and count enhancement totals -----
pool = []  # list of dicts, one per card copy
enh_totals = defaultdict(int)
missing_images = []

for title, copies in title_counter.items():
    card = json_map.get(title)
    if not card:
        # skip missing; logged earlier
        continue

    # determine house (previous scripts usually used card['houses'][0])
    houses = card.get('houses') or card.get('house') or []
    if isinstance(houses, list) and houses:
        house = houses[0]
    elif isinstance(houses, str) and houses:
        house = houses
    else:
        house = 'Unknown'

    # Ensure house folder exists
    folder_path = os.path.join(CARDS_DIR, house)
    os.makedirs(folder_path, exist_ok=True)

    # image names and relative path (use forward slashes)
    safe_name = title.replace(' ', '_')
    img_name = f"{safe_name}.png"
    relative_img_path = f"{house}/{img_name}".replace('\\', '/')
    img_path = os.path.join(folder_path, img_name)

    # read amber (top-level)
    amber_val = safe_int(card.get('amber', 0), 0)

    # Count enhancements declared in JSON (treated as per-copy value)
    for ek, _label in ENH_KEYS:
        raw = get_field(card, ek, 0)
        enh_count = safe_int(raw, 0)
        # Multiply by number of copies — these are the total enhancement units to distribute
        enh_totals[ek] += enh_count * copies

    # create pool entries (one per copy)
    for i in range(copies):
        max_enh = max(0, 5 - amber_val)
        entry = {
            'house': house,
            'title': title,
            'img_name': img_name,
            'img_path': relative_img_path,
            'is_token': "Yes" if card.get('token', False) else "",
            'amber': amber_val,
            'max_enh': max_enh,
            'current_enh_total': 0,
            'enh_counts': {ek: 0 for ek, _ in ENH_KEYS},
            # keep URL for potential download
            'img_url': card.get('cardTitleUrl') or ''
        }
        pool.append(entry)

log_write(f"Built pool with {len(pool)} copies (one per card copy).")
log_write("Total enhancements read from JSON (units to assign):")
for ek, _ in ENH_KEYS:
    log_write(f" - {ek}: {enh_totals[ek]}")

# ----- Assign enhancements randomly, respecting per-card max -----
random.seed()

for ek, label in ENH_KEYS:
    to_assign = int(enh_totals[ek])
    assigned = 0
    for _ in range(to_assign):
        eligible = [idx for idx, p in enumerate(pool) if p['current_enh_total'] < p['max_enh']]
        if not eligible:
            log_write(f"Could not assign remaining {to_assign - assigned} units of {ek}: no eligible cards left.")
            break
        idx = random.choice(eligible)
        pool[idx]['enh_counts'][ek] += 1
        pool[idx]['current_enh_total'] += 1
        assigned += 1
    log_write(f"Assigned {assigned}/{to_assign} of {ek}.")

# ----- Optionally download images (skip with SKIP_IMAGE_DOWNLOAD=1) -----
skip_images = os.environ.get('SKIP_IMAGE_DOWNLOAD') == '1'
for p in pool:
    if skip_images:
        continue
    img_url = p.get('img_url')
    if not img_url:
        missing_images.append(p['title'])
        continue
    # only download if not already present or zero bytes
    full_img_path = os.path.join(CARDS_DIR, p['img_path'].replace('/', os.sep))
    if os.path.exists(full_img_path) and os.path.getsize(full_img_path) > 0:
        continue
    try:
        r = requests.get(img_url, stream=True, timeout=30)
        r.raise_for_status()
        # ensure dir exists
        os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
        with open(full_img_path, 'wb') as fh:
            for chunk in r.iter_content(8192):
                fh.write(chunk)
    except Exception as e:
        missing_images.append(p['title'])
        log_write(f"Failed to download image for '{p['title']}': {e}")

if missing_images:
    log_write(f"Images missing/unfetched for {len(set(missing_images))} distinct cards (sample): {', '.join(list(set(missing_images))[:20])}")

# ----- Write cube.md (one row per copy) -----
headers = [
    'House', 'CardTitle', 'Image Link', 'Is Token', 'Amber'
] + [label for _, label in ENH_KEYS]

with open(OUTPUT_MD, 'w', encoding='utf-8') as md:
    md.write('| ' + ' | '.join(headers) + ' |\n')
    md.write('| ' + ' | '.join(['---'] * len(headers)) + ' |\n')
    for p in pool:
        img_md = f"[{p['img_name']}]({p['img_path']})"
        row_vals = [
            p['house'],
            p['title'],
            img_md,
            p['is_token'],
            p['amber']
        ]
        # append enhancement counts in same ENH_KEYS order
        for ek, _ in ENH_KEYS:
            row_vals.append(p['enh_counts'].get(ek, 0))
        # escape pipes to keep markdown safe
        safe_row = [str(v).replace('|', '\\|') for v in row_vals]
        md.write('| ' + ' | '.join(safe_row) + ' |\n')

log_write(f"Wrote {len(pool)} rows to {OUTPUT_MD} (one per card copy).")
log_write("Cube generation complete.")

print(f"Done — wrote {OUTPUT_MD} and log to {LOG_FILE}. (SKIP_IMAGE_DOWNLOAD={'yes' if skip_images else 'no'})")