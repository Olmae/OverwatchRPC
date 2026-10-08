from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageEnhance

from owrpc_app.portraits import scoreboard_hero, templates
from owrpc_app.mode_icons import scoreboard_mode

FIXTURES = Path(__file__).parent / 'fixtures'


class PortraitTests(unittest.TestCase):
    def test_independent_scoreboard_portraits_across_viewport_sizes(self):
        for key, expected in [('dva', 'D.Va'), ('baptiste', 'Baptiste'),
                              ('ashe', 'Ashe'), ('junker-queen', 'Junker Queen')]:
            with Image.open(FIXTURES / 'tab-portraits' / (key + '.png')) as source:
                for size in ((1584, 891), (3440, 1440)):
                    with self.subTest(hero=expected, size=size):
                        image = Image.new('RGB', size, (15, 20, 36))
                        side, top = round(.158 * size[1]), round(.145 * size[1])
                        left = round(size[0] * (.627 if size[0]/size[1] < 2 else .58))
                        image.paste(source.resize((side, side)), (left, top))
                        self.assertEqual(scoreboard_hero(image), expected)
                        dim = ImageEnhance.Brightness(image).enhance(.5)
                        self.assertEqual(scoreboard_hero(dim), expected)

    def test_empty_panel_and_ambiguous_artwork_are_rejected(self):
        self.assertIsNone(scoreboard_hero(Image.new('RGB', (1584, 891), (31, 40, 59))))
        reference = next(row for row in templates() if row[0] == 'D.Va')
        duplicate = ('Unknown lookalike', *reference[1:])
        with patch('owrpc_app.portraits.templates', return_value=(reference, duplicate)):
            with Image.open(FIXTURES / 'tab-portraits' / 'dva.png') as source:
                image = Image.new('RGB', (1584, 891))
                image.paste(source.resize((141, 141)), (993, 129))
                self.assertIsNone(scoreboard_hero(image))

    def test_independent_mode_headers_and_unknown_glyph(self):
        for key, expected in [('control', 'Control'), ('escort', 'Escort'), ('practice', None)]:
            with self.subTest(mode=key), Image.open(FIXTURES / 'mode-icons' / (key + '.png')) as header:
                image = Image.new('RGB', (3440, 1440), (15, 20, 36))
                image.paste(header, (round(.65 * 3440), round(.025 * 1440)))
                self.assertEqual(scoreboard_mode(image), expected)
