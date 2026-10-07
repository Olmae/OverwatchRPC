import string
import unittest

from owrpc_app.i18n import LANGUAGES, TEXT, normalize_language, tr
from owrpc_app.model import Settings, Status, build_payload


class LocalizationTests(unittest.TestCase):
    def test_all_nine_languages_have_complete_matching_placeholders(self):
        self.assertEqual(len(LANGUAGES), 9)
        formatter = string.Formatter()
        for key, translations in TEXT.items():
            expected = {field for _, field, _, _ in formatter.parse(key) if field}
            self.assertEqual(set(translations), set(LANGUAGES), key)
            for language, value in translations.items():
                self.assertTrue(value.strip(), (key, language))
                self.assertEqual(expected, {field for _, field, _, _ in formatter.parse(value) if field})

    def test_locale_mapping_and_fallback(self):
        self.assertEqual(normalize_language('ru_RU'), 'ru')
        self.assertEqual(normalize_language('zh-HK'), 'zh-TW')
        self.assertEqual(normalize_language('pt_PT'), 'pt-BR')
        self.assertEqual(normalize_language('de_DE'), 'de')
        self.assertEqual(normalize_language('fr_FR'), 'fr')
        self.assertEqual(normalize_language('xx_XX'), 'en')
        self.assertEqual(tr('Map', 'ru'), 'Карта')
        self.assertEqual(tr('Unknown custom text', 'ru'), 'Unknown custom text')

    def test_settings_validate_language_and_keep_custom_fields(self):
        self.assertEqual(Settings.from_dict({'language': 'broken'}).language, 'auto')
        self.assertEqual(Settings.from_dict({'language': 'ru', 'hero': 'Ana'}).hero, 'Ana')

    def test_payload_is_translated_without_changing_identity_or_timer(self):
        status = Status(phase='match', hero='Ana', map_name='Busan', mode='Quick Play', started_at=42)
        payload = build_payload(Settings(language='ru'), status)
        self.assertIn('Быстрая игра', payload['details'])
        self.assertIn('Ana', payload['state'])
        self.assertEqual(payload['start'], 42)
        self.assertEqual(status.hero, 'Ana')
        self.assertEqual(build_payload(Settings(language='ru', details_override='Custom'), status)['details'], 'Custom')
