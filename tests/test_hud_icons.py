from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageEnhance

from owrpc_app.catalog import load_catalog, resource_dir
from owrpc_app.detection import Word
from owrpc_app.hud_icons import hud_hero, match_slots, own_hud, signature
from owrpc_app.ocr import analyze_image


def frame(key):
    image = Image.new('RGB', (3440, 1440))
    with Image.open(Path(__file__).parent/'fixtures'/'hud-icons'/(key+'.png')) as crop:
        image.paste(crop, (2504, 1123))
    return image


def glyph(key):
    with Image.open(resource_dir()/'hud-icons'/(key+'.png')) as source:
        return signature(source.convert('RGBA').getchannel('A'))


class HudIconTests(unittest.TestCase):
    def test_independent_real_hud_icons_and_resized_capture(self):
        for key, hero in (('reaper', 'Reaper'), ('ramattra', 'Ramattra')):
            image = frame(key)
            with self.subTest(hero=hero):
                self.assertEqual(hud_hero(image), hero)
                self.assertEqual(hud_hero(image.resize((2048, 857))), hero)
                self.assertEqual(hud_hero(ImageEnhance.Brightness(image).enhance(.8)), hero)

    def test_weapon_supports_one_ready_ability_when_another_is_on_cooldown(self):
        from PIL import ImageDraw
        image = frame('reaper')
        ImageDraw.Draw(image).rectangle((2855, 1200, 2960, 1340), fill=(20, 170, 150))
        self.assertEqual(hud_hero(image), 'Reaper')

    def test_single_duplicate_conflicting_and_repeated_weapon_crops_abstain(self):
        a, b = glyph('genji-1'), glyph('reaper-2')
        self.assertIsNone(match_slots([[a]]))
        self.assertIsNone(match_slots([[a], [a]]))
        self.assertIsNone(match_slots([[a], [b]]))
        self.assertIsNone(match_slots([[a, glyph('genji-0')]], weapon_slot=0))
        self.assertIsNone(hud_hero(Image.new('RGB', (3440, 1440), 'white')))

    def test_own_name_and_replay_guard_are_independent_of_interface_language(self):
        english = Word('OlmaeUwU', .095, .89, .06, .02)
        russian = Word('Игрок', .095, .89, .06, .02)
        self.assertTrue(own_hud([english], 'OlmaeUwU'))
        self.assertTrue(own_hud([russian], 'Игрок'))
        self.assertFalse(own_hud([english], 'AnotherPlayer'))
        self.assertFalse(own_hud([english], ''))
        self.assertFalse(own_hud([english, Word('SPECTATING', .4, .05, .1, .02)], 'OlmaeUwU'))
        self.assertFalse(own_hud([english, Word('ПОВТОР', .4, .05, .1, .02)], 'OlmaeUwU'))

    def test_hud_integration_requires_own_name_and_does_not_apply_in_menus(self):
        words = [Word('250', .1, .82, .03, .02), Word('250', .15, .82, .03, .02),
                 Word('8', .92, .88, .02, .02), Word('8', .95, .88, .02, .02),
                 Word('OlmaeUwU', .095, .89, .06, .02)]
        catalog = load_catalog()
        self.assertEqual(analyze_image(frame('reaper'), words, catalog, 'OlmaeUwU').hero, 'Reaper')
        result = analyze_image(frame('reaper'), words[-1:], catalog, 'OlmaeUwU')
        self.assertEqual((result.phase, result.scene, result.hero), ('match', 'hud', 'Reaper'))
        result = analyze_image(frame('reaper'), words[-1:]+[Word('DMG', .4, .15, .03, .02)],
                               catalog, 'OlmaeUwU')
        self.assertIsNone(result.phase)
        self.assertIsNone(analyze_image(frame('reaper'), words, catalog, 'AnotherPlayer').hero)
        result = analyze_image(frame('reaper'), words+[Word('HEROES', .03, .02, .1, .02)],
                               catalog, 'OlmaeUwU')
        self.assertEqual(result.phase, 'menus')
        self.assertIsNone(result.hero)
        for extra in ([Word('SEARCHING', .46, .02, .1, .02)],
                      [Word(label, x, .15, .01, .02) for label, x in [('E', .38), ('A', .41), ('D', .44)]]):
            with patch('owrpc_app.hud_icons.hud_hero') as match:
                analyze_image(frame('reaper'), words+extra, catalog, 'OlmaeUwU')
                match.assert_not_called()
