import unittest
from owrpc_app.model import Settings

class SettingsUpdateTests(unittest.TestCase):
    def test_checks_default_on_and_saved_opt_out_survives(self):
        self.assertTrue(Settings().check_updates)
        self.assertTrue(Settings().auto_catalog)
        settings = Settings.from_dict({'check_updates': False, 'auto_catalog': False, 'ocr_enabled': False})
        self.assertFalse(settings.check_updates)
        self.assertFalse(settings.auto_catalog)
        self.assertFalse(settings.ocr_enabled)

    def test_legacy_ocr_language_is_normalized(self):
        for value in ('rus', 'ru-RU', 'rus+eng'):
            self.assertEqual(Settings.from_dict({'ocr_language': value}).ocr_language, 'rus')
        self.assertEqual(Settings.from_dict({'ocr_language': 'unsupported'}).ocr_language, 'eng')
