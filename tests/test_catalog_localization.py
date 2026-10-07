import copy
import unittest

from owrpc_app.catalog import load_catalog
from owrpc_app.detection import catalog_name
from owrpc_app.model import Settings, Status, build_payload
from scripts.refresh_catalog import preserve_localized_names


class CatalogLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_every_russian_hero_resolves_to_canonical_identity(self):
        for hero in self.catalog['heroes']:
            with self.subTest(hero=hero['name']):
                localized = hero.get('localized_names', {}).get('ru')
                self.assertTrue(localized)
                self.assertEqual(catalog_name(localized.upper(), self.catalog['heroes']), hero['name'])

    def test_russian_map_names_resolve(self):
        for text, name in [('КОНТРОЛЬ | БАШНЯ ЛИЦЗЯН', 'Lijiang Tower'),
                           ('КОНТРОЛЬ | НЕПАЛ', 'Nepal'), ('СОПРОВОЖДЕНИЕ | ГАВАНА', 'Havana')]:
            self.assertEqual(catalog_name(text, self.catalog['maps']), name)

    def test_bounded_fuzzy_matching_uses_localized_phrases(self):
        for text, name in [('МОЙРД', 'Moira'), ('КУЛАК СМЕРТИИ', 'Doomfist'),
                           ('КОРОЛЕВА СТЕРВЯТНИКОЗ', 'Junker Queen')]:
            self.assertEqual(catalog_name(text, self.catalog['heroes'], fuzzy=True), name)
        self.assertIsNone(catalog_name('АН', self.catalog['heroes'], fuzzy=True))
        self.assertIsNone(catalog_name('НЕИЗВЕСТНЫЙ ГЕРОЙ', self.catalog['heroes'], fuzzy=True))
        self.assertIsNone(catalog_name('МОЙРА АНА', self.catalog['heroes'], fuzzy=True))

    def test_refresh_preserves_localizations_by_key_without_mutating_previous(self):
        previous = {'heroes': [{'key': 'ana', 'name': 'Ana', 'localized_names': {'ru': 'Ана'}}],
                    'maps': [{'key': 'nepal', 'name': 'Nepal', 'localized_names': {'ru': 'Непал'}}]}
        snapshot = copy.deepcopy(previous)
        refreshed = {'heroes': [{'key': 'ana', 'name': 'Ana'}, {'key': 'new', 'name': 'New'}],
                     'maps': [{'key': 'nepal', 'name': 'Nepal'}]}
        preserve_localized_names(refreshed, previous)
        self.assertEqual(refreshed['heroes'][0]['localized_names'], {'ru': 'Ана'})
        self.assertEqual(refreshed['maps'][0]['localized_names'], {'ru': 'Непал'})
        self.assertNotIn('localized_names', refreshed['heroes'][1])
        refreshed['heroes'][0]['localized_names']['ru'] = 'changed'
        self.assertEqual(previous, snapshot)

    def test_russian_presence_uses_names_without_changing_status_identity(self):
        hero = next(h for h in self.catalog['heroes'] if h['name'] == 'Mercy')
        map_info = next(m for m in self.catalog['maps'] if m['name'] == 'Nepal')
        status = Status(phase='match', hero='Mercy', map_name='Nepal')
        payload = build_payload(Settings(language='ru'), status, hero, map_info)
        self.assertIn('Ангел', payload['state'])
        self.assertIn('Непал', payload['details'])
        self.assertEqual(payload.get('small_text'), 'Ангел')
        self.assertEqual((status.hero, status.map_name), ('Mercy', 'Nepal'))


class SpatialLocalizedTextTests(unittest.TestCase):
    def test_ocr_letter_heights_do_not_reverse_words_on_one_line(self):
        from owrpc_app.detection import Word, text_in
        words = [Word('БАШНЯ', .678, .0522, .057, .0223),
                 Word('ЛИЦЗЯН', .739, .0488, .067, .0272)]
        self.assertEqual(text_in(words, (.65, 0, 1, .09)), 'БАШНЯ ЛИЦЗЯН')

    def test_distinct_lines_keep_vertical_reading_order(self):
        from owrpc_app.detection import Word, text_in
        words = [Word('SECOND', .1, .06, .1, .02), Word('LINE', .3, .06, .1, .02),
                 Word('FIRST', .5, .02, .1, .02)]
        self.assertEqual(text_in(words, (0, 0, 1, .1)), 'FIRST SECOND LINE')
