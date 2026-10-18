from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageEnhance

from owrpc_app.portraits import scoreboard_hero, templates
from owrpc_app.mode_icons import scoreboard_mode

FIXTURES = Path(__file__).parent / 'fixtures'


class PortraitTests(unittest.TestCase):
    def test_verified_assembly_portrait_overrides_stale_title_only_during_selection(self):
        from owrpc_app.detection import Word
        from owrpc_app.ocr import analyze_image
        image = Image.new('RGB', (3440, 1440))
        catalog = {'heroes': [{'name': 'Echo'}, {'name': 'Freja'}], 'maps': []}
        words = [Word('SELECT A HERO', .03, .12, .2, .04),
                 Word('FREJA', .85, .03, .1, .06)]
        with patch('owrpc_app.portraits.assembly_hero', return_value='Echo'):
            self.assertEqual(analyze_image(image, words, catalog, 'OWNNAME').hero, 'Echo')
        with patch('owrpc_app.portraits.assembly_hero', return_value=None):
            self.assertEqual(analyze_image(image, words, catalog, 'OWNNAME').hero, 'Freja')
        with patch('owrpc_app.portraits.assembly_hero') as match:
            analyze_image(image, [Word('HEROES', .03, .02, .1, .02)], catalog, 'OWNNAME')
            match.assert_not_called()

    def test_continue_uses_compact_assembly_and_requires_unique_owner(self):
        from owrpc_app.detection import Word
        from owrpc_app.portraits import assembly_owner, assembly_layout
        image = Image.new('RGB', (3440, 1440))
        button = Word('CONTINUE', .48, .90, .05, .02)
        own = Word('OWNNAME', .299, .634, .03, .02)
        self.assertEqual(assembly_layout(image, [button])[0][0], .315)
        self.assertEqual(assembly_owner(image, [button, own], 'OWNNAME'), own)
        other = Word('OWNNAME', .393, .634, .03, .02)
        self.assertIsNone(assembly_owner(image, [button, own, other], 'OWNNAME'))

    def test_assembly_requires_own_nickname_and_rejects_blank_portrait(self):
        from owrpc_app.detection import Word
        from owrpc_app.portraits import assembly_hero
        words = [Word('OWNNAME', .17, .64, .045, .02)]
        blank = Image.new('RGB', (2560, 1440), (30, 40, 50))
        self.assertIsNone(assembly_hero(blank, words, 'OWNNAME'))
        self.assertIsNone(assembly_hero(blank, words, 'OTHERNAME'))
        self.assertIsNone(assembly_hero(blank, words, ''))
        wide = Image.new('RGB', (3440, 1440), (30, 40, 50))
        wide_words = [Word('OWNNAME', .256, .64, .031, .02)]
        self.assertIsNone(assembly_hero(wide, wide_words, 'OWNNAME'))
        self.assertIsNone(assembly_hero(wide, wide_words, 'OTHERNAME'))
        self.assertIsNone(assembly_hero(wide, wide_words*2, 'OWNNAME'))
        self.assertIsNone(assembly_hero(wide, words, 'OWNNAME'))

    def test_assembly_name_variants_merge_only_within_the_same_player_slot(self):
        from owrpc_app.detection import Word
        from owrpc_app.portraits import assembly_owner
        image = Image.new('RGB', (3440, 1440))
        ready = Word('READY', .48, .90, .03, .02)
        exact = Word('OWNNAME', .299, .634, .03, .02)
        variant = Word('OWNN4ME', .300, .634, .03, .02)
        self.assertEqual(assembly_owner(image, [ready, variant, exact], 'OWNNAME'), exact)
        other = Word('OWNNAME', .393, .634, .03, .02)
        self.assertIsNone(assembly_owner(image, [ready, exact, other], 'OWNNAME'))

    def test_shifted_midtown_panel_portrait(self):
        with Image.open(FIXTURES / 'tab-portraits' / 'ramattra.png') as source:
            for size in ((2562, 1440), (1584, 891)):
                image = Image.new('RGB', size, (15, 20, 36))
                side = round(.158 * size[1])
                image.paste(source.resize((side, side)),
                            (round(.608 * size[0]), round(.145 * size[1])))
                self.assertEqual(scoreboard_hero(image), 'Ramattra')

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
