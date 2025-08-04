import os  # for file and directory operations
import json  # for parsing JSON data
import csv  # for writing extraCardInfo to a CSV
import requests  # for HTTP requests to download images
from collections import Counter  # to count occurrences of card titles

# Base directory for all card-related files
CARDS_DIR = 'cards'
CARDS_TXT = os.path.join(CARDS_DIR, 'cards.txt')
CARDS_JSON = os.path.join(CARDS_DIR, 'cards.json')
OUTPUT_MD = os.path.join(CARDS_DIR, 'cube.md')
OUTPUT_CSV = os.path.join(CARDS_DIR, 'cube_stats.csv')
LOG_FILE = os.path.join(CARDS_DIR, 'cube.log')

# Count all card titles (including duplicates)
with open(CARDS_TXT, 'r', encoding='utf-8') as f:
    all_titles = [line.strip() for line in f if line.strip()]
    title_counter = Counter(all_titles)
    titles = set(title_counter.keys())

# Load the JSON data containing all cards
with open(CARDS_JSON, 'r', encoding='utf-8') as f:
    cards = json.load(f)

# Extract all cardTitle values present in the JSON
json_titles = {card.get('cardTitle') for card in cards if 'cardTitle' in card}

# Initialize the log file
with open(LOG_FILE, 'w', encoding='utf-8') as log:
    log.write('=== CUBE GENERATION LOG ===\n')
    missing = titles - json_titles
    if missing:
        log.write('Missing JSON entries for these titles:\n')
        for title in sorted(missing):
            log.write(f"- {title}\n")
    else:
        log.write('All titles found in JSON.\n')

# Cleanup: remove obsolete images
with open(LOG_FILE, 'a', encoding='utf-8') as log:
    log.write('\nCleaning up obsolete images...\n')
for sub in os.listdir(CARDS_DIR):
    sub_path = os.path.join(CARDS_DIR, sub)
    if os.path.isdir(sub_path):
        for file in os.listdir(sub_path):
            if file.lower().endswith('.png'):
                base = os.path.splitext(file)[0].replace('_', ' ')
                if base not in titles:
                    try:
                        os.remove(os.path.join(sub_path, file))
                        with open(LOG_FILE, 'a', encoding='utf-8') as log:
                            log.write(f"Removed obsolete image: {sub}/{file}\n")
                    except Exception as e:
                        with open(LOG_FILE, 'a', encoding='utf-8') as log:
                            log.write(f"Failed to remove {sub}/{file}: {e}\n")

# Prepare data structures for markdown and CSV
markdown_rows = []  # Markdown rows (House, CardTitle, Nr of Copies, Link)
csv_rows = []  # CSV rows for stats

# Process each card in the JSON
for card in cards:
    title = card.get('cardTitle')
    if title not in titles:
        continue

    houses = card.get('houses', [])
    if not houses:
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(f"No house found for '{title}', skipping.\n")
        continue

    house = houses[0]
    folder_path = os.path.join(CARDS_DIR, house)
    os.makedirs(folder_path, exist_ok=True)

    # Normalize filename (spaces → underscores)
    safe_name = title.replace(' ', '_')
    img_name = f"{safe_name}.png"
    img_path = os.path.join(folder_path, img_name)

    # Download image
    try:
        img_url = card.get('cardTitleUrl')
        if not img_url:
            raise ValueError("Missing 'cardTitleUrl'")
        r = requests.get(img_url, stream=True)
        r.raise_for_status()
        with open(img_path, 'wb') as img_file:
            for chunk in r.iter_content(8192):
                img_file.write(chunk)
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(f"Downloaded image for '{title}' as {house}/{img_name}\n")
    except Exception as e:
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(f"Failed to download image for '{title}': {e}\n")

    # Markdown row with forward slashes in path for compatibility
    relative_img_path = f"{house}/{img_name}".replace('\\', '/')
    img_markdown = f"[{img_name}]({relative_img_path})"
    count = title_counter[title]
    markdown_rows.append((house, f"| {house} | {title} | {count} | {img_markdown} |"))

    # Extract and collect extraCardInfo stats using flat key names
    def fmt(value):
        return str(value).replace('.', ',') if isinstance(value, float) else value

    csv_rows.append([
        house,
        title,
        fmt(card.get('extraCardInfo.amberControl', '')),
        fmt(card.get('extraCardInfo.expectedAmber', '')),
        fmt(card.get('extraCardInfo.artifactControl', '')),
        fmt(card.get('extraCardInfo.creatureControl', '')),
        fmt(card.get('extraCardInfo.efficiency', '')),
        fmt(card.get('extraCardInfo.recursion', ''))
    ])

# Sort markdown table by house
markdown_rows.sort(key=lambda x: x[0])

# Write markdown file (image links only)
with open(OUTPUT_MD, 'w', encoding='utf-8') as md:
    md.write('| House | CardTitle | Nr of Copies | ImagePath |\n')
    md.write('| --- | --- | --- | --- |\n')
    for _, row in markdown_rows:
        md.write(row + '\n')

# Write CSV file for card stats with semicolon delimiter
with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow([
        'House', 'CardTitle', 'AmberControl', 'ExpectedAmber', 'ArtifactControl',
        'CreatureControl', 'Efficiency', 'Recursion'
    ])
    writer.writerows(csv_rows)

print("Done: cube.md and cube_stats.csv written. Images and log updated.")