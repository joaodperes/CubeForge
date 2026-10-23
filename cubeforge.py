"""Run CubeForge with a full, enhancement-test, or custom cube.

Examples:
    python cubeforge.py
    python cubeforge.py --preset enhancement-test --seed 42
    python cubeforge.py --preset custom --card-list my_cube.txt --prepare-only
    DOK_API_KEY=... python cubeforge.py --refresh-cards
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
PRESETS = {
    'full': ROOT / 'presets' / 'full.txt',
    'enhancement-test': ROOT / 'presets' / 'enhancement-test.txt',
}
DOK_URL = 'https://decksofkeyforge.com/public-api/v1/cards'
GENERATED = ROOT / 'cards' / 'generated'


def flatten_card_fields(value, prefix=''):
    """Preserve DoK array fields and flatten nested objects to dotted keys."""
    result = {}
    for key, data in value.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(data, dict):
            result.update(flatten_card_fields(data, path))
        else:
            result[path] = data
    return result


def refresh_card_database(destination):
    """Update local DoK metadata; never commit or print an API key."""
    key = os.environ.get('DOK_API_KEY')
    if not key:
        raise ValueError('Set DOK_API_KEY in your environment to use --refresh-cards.')
    req = Request(DOK_URL, headers={'Api-Key': key, 'Accept': 'application/json'})
    with urlopen(req, timeout=90) as response:
        records = json.load(response)
    if not isinstance(records, list) or not records or not isinstance(records[0], dict):
        raise ValueError('DoK did not return a card array; existing metadata left intact.')
    flattened = [flatten_card_fields(card) for card in records]
    if not all(isinstance(card.get('cardTitle'), str) for card in flattened):
        raise ValueError('DoK response is missing card titles; existing metadata left intact.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(flattened, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Updated card metadata: {len(flattened)} cards -> {destination}')


def parser():
    p = argparse.ArgumentParser(description='Prepare and play CubeForge without manual file editing.')
    p.add_argument('--preset', choices=['full', 'enhancement-test', 'custom'], default='full')
    p.add_argument('--card-list', type=Path, help='One card title per line (required for custom preset)')
    p.add_argument('--card-data', type=Path, default=ROOT / 'cards' / 'cards.json',
                   help='Optional alternative DoK JSON database')
    p.add_argument('--players', type=int, default=3, help='Total players, including the human (default: 3)')
    p.add_argument('--seed', type=int, help='Reproduce the same randomized enhancements and packs')
    p.add_argument('--no-enhancements', action='store_true', help='Disable all generated enhancements')
    p.add_argument('--download-images', action='store_true', help='Fetch missing card images')
    p.add_argument('--refresh-cards', action='store_true', help='Download DoK data (requires DOK_API_KEY)')
    p.add_argument('--prepare-only', action='store_true', help='Generate and validate, without opening the UI')
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.preset == 'custom':
        if not args.card_list:
            p.error('--preset custom requires --card-list')
        card_list = args.card_list.expanduser().resolve()
    else:
        if args.card_list:
            p.error('--card-list requires --preset custom')
        card_list = PRESETS[args.preset]
    if not card_list.is_file():
        p.error(f'Card list not found: {card_list}')
    card_data = args.card_data.expanduser().resolve()
    if args.refresh_cards:
        refresh_card_database(card_data)
    if not card_data.is_file():
        p.error(f'Card database not found: {card_data}')

    GENERATED.mkdir(parents=True, exist_ok=True)
    output_name = f"{args.preset}{'-plain' if args.no_enhancements else '-enhanced'}.md"
    output = GENERATED / output_name
    log = output.with_suffix('.log')
    env = os.environ.copy()
    env.update({
        'CUBEFORGE_CARD_LIST': str(card_list),
        'CUBEFORGE_CARDS_JSON': str(card_data),
        'CUBEFORGE_CUBE_OUTPUT': str(output),
        'CUBEFORGE_CUBE_PATH': str(output),
        'CUBEFORGE_LOG_OUTPUT': str(log),
        'CUBEFORGE_ENABLE_ENHANCEMENTS': '0' if args.no_enhancements else '1',
        'CUBEFORGE_NUM_PLAYERS': str(args.players),
        'SKIP_IMAGE_DOWNLOAD': '0' if args.download_images else '1',
    })
    if args.seed is not None:
        env['CUBEFORGE_SEED'] = str(args.seed)
    else:
        env.pop('CUBEFORGE_SEED', None)

    subprocess.run([sys.executable, str(ROOT / 'cube_generator.py')],
                   cwd=ROOT, env=env, check=True)

    # Validate using the same pool parser that powers the UI.
    previous_cube = os.environ.get('CUBEFORGE_CUBE_PATH')
    os.environ['CUBEFORGE_CUBE_PATH'] = str(output)
    try:
        from draft_simulator import load_cube_md, build_card_pool
        pool, _ = build_card_pool(load_cube_md(output))
    finally:
        if previous_cube is None:
            os.environ.pop('CUBEFORGE_CUBE_PATH', None)
        else:
            os.environ['CUBEFORGE_CUBE_PATH'] = previous_cube

    max_players = len(pool) // 60
    if args.players < 2 or args.players > max_players:
        p.error(f'{len(pool)} draftable cards support 2–{max_players} players; requested {args.players}.')
    if 'Missing JSON entries for these titles:' in log.read_text(encoding='utf-8'):
        print(f'Warning: some titles were not resolved. See {log}', file=sys.stderr)
    print(f'Prepared {len(pool)} draftable card copies for {args.players} players.')
    print(f'Card cube: {output}')
    if not args.prepare_only:
        subprocess.run([sys.executable, str(ROOT / 'draft_ui.py')],
                       cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'CubeForge error: {exc}', file=sys.stderr)
        sys.exit(1)
