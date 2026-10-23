"""Headless regression tests for cube generation and enhancement-aware drafting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from draft_simulator import (
    build_card_pool, bot_pick, enhancement_score, get_bot_logs,
    initialize_bot_logs, load_cube_md
)

ROOT = Path(__file__).resolve().parents[1]


class DraftTests(unittest.TestCase):
    def setUp(self):
        initialize_bot_logs(2)

    def test_enhancements_make_identical_card_copies_distinct(self):
        plain = {'House': 'Dis', 'CardTitle': 'Vapor Imp', 'CopyId': '1'}
        enhanced = {**plain, 'CopyId': '2', 'Enh.Amber': 2, 'Enh.Draw': 1}
        self.assertGreater(enhancement_score(enhanced), enhancement_score(plain))
        stats = {'Vapor Imp': {'amberControl': 0, 'expectedAmber': 0,
                  'creatureControl': 0, 'artifactControl': 0,
                  'efficiency': 0, 'recursion': 0, 'traits': [], 'synergies': []}}
        chosen = bot_pick([plain, enhanced], [], stats, {'Vapor Imp': 'Dis'}, 1)
        self.assertEqual(chosen['CopyId'], '2')
        self.assertEqual(get_bot_logs()[1][-1]['copy_id'], '2')

    def test_parser_keeps_copy_ids_and_excludes_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cube.md'
            path.write_text(
                '| House | CardTitle | CopyId | Image Link | Is Token | Amber | Enh.Amber |\n'
                '| --- | --- | --- | --- | --- | --- | --- |\n'
                '| Dis | Vapor Imp | copy-1 | [card](Dis/Vapor_Imp.png) | | 0 | 2 |\n'
                '| Dis | Snare | token-1 | [token](Dis/Snare.png) | Yes | 0 | 0 |\n',
                encoding='utf-8')
            cards = load_cube_md(path)
            pool, _ = build_card_pool(cards)
            self.assertEqual(len(pool), 1)
            self.assertEqual(pool[0]['CopyId'], 'copy-1')
            self.assertEqual(pool[0]['Enh.Amber'], 2)

    def test_generator_normalizes_titles_and_is_seeded(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            title_list = base / 'titles.txt'
            metadata = base / 'data.json'
            cube = base / 'out.md'
            log = base / 'out.log'
            title_list.write_text("Po's Pixies\nPo's Pixies\nPo's Pixies\n", encoding='utf-8')
            metadata.write_text(json.dumps([{
                'cardTitle': 'Pos Pixies', 'houses': ['Untamed'],
                'amber': 0, 'token': False,
                'extraCardInfo.enhancementDraw': 2,
            }]), encoding='utf-8')
            env = dict(os.environ,
                CUBEFORGE_CARD_LIST=str(title_list),
                CUBEFORGE_CARDS_JSON=str(metadata),
                CUBEFORGE_CUBE_OUTPUT=str(cube),
                CUBEFORGE_LOG_OUTPUT=str(log),
                CUBEFORGE_SEED='1234',
                CUBEFORGE_ENABLE_ENHANCEMENTS='1',
                SKIP_IMAGE_DOWNLOAD='1')
            cmd = [sys.executable, str(ROOT / 'cube_generator.py')]
            subprocess.run(cmd, env=env, cwd=ROOT, check=True, capture_output=True)
            first = cube.read_text(encoding='utf-8')
            subprocess.run(cmd, env=env, cwd=ROOT, check=True, capture_output=True)
            self.assertEqual(first, cube.read_text(encoding='utf-8'))
            pool, _ = build_card_pool(load_cube_md(cube))
            self.assertEqual(len(pool), 3)
            self.assertEqual(len({card['CopyId'] for card in pool}), 3)
            self.assertEqual(sum(card['Enh.Draw'] for card in pool), 6)
            self.assertTrue(all(card['CardTitle'] == 'Pos Pixies' for card in pool))


if __name__ == '__main__':
    unittest.main()
