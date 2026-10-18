import json
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from owrpc_app.native_ocr import WindowsOCR


class NativeOcrCacheTests(unittest.TestCase):
    def bridge(self):
        bridge = WindowsOCR()
        bridge.process = Mock()
        bridge.process.poll.return_value = None
        return bridge

    def reply(self, bridge, text='HEROES', count=1):
        bridge.lines.put(json.dumps({'width': 100, 'height': 50, 'words': [
            {'text': text, 'x': 10, 'y': 10, 'width': 30, 'height': 20} for _ in range(count)]}))

    def test_exact_pixels_reuse_words_and_return_an_independent_list(self):
        bridge = self.bridge()
        image = Image.new('RGB', (100, 50), 'white')
        self.reply(bridge)
        first = bridge.words(image)
        first.clear()
        second = bridge.words(image.copy())
        self.assertEqual(second[0].text, 'HEROES')
        self.assertEqual(bridge.process.stdin.write.call_count, 1)
        self.assertEqual(len(bridge.cache), 1)

    def test_one_changed_pixel_or_dimensions_require_a_new_read(self):
        bridge = self.bridge()
        image = Image.new('RGB', (100, 50), 'white')
        self.reply(bridge, 'OLD')
        bridge.words(image)
        image.putpixel((99, 49), (0, 0, 0))
        self.reply(bridge, 'NEW')
        self.assertEqual(bridge.words(image)[0].text, 'NEW')
        self.reply(bridge, 'RESIZED')
        self.assertEqual(bridge.words(image.resize((50, 100)))[0].text, 'RESIZED')
        self.assertEqual(bridge.process.stdin.write.call_count, 3)

    def test_language_change_and_close_clear_the_cache(self):
        bridge = self.bridge()
        self.reply(bridge)
        bridge.words(Image.new('RGB', (100, 50)))
        bridge.configure('rus')
        self.assertEqual(bridge.language, 'ru-RU')
        self.assertFalse(bridge.cache)
        self.assertIsNone(bridge.process)

    def test_empty_reading_is_cached_without_another_native_request(self):
        bridge = self.bridge()
        image = Image.new('RGB', (100, 50))
        self.reply(bridge, count=0)
        self.assertEqual(bridge.words(image), [])
        self.assertEqual(bridge.words(image), [])
        self.assertEqual(bridge.process.stdin.write.call_count, 1)

    def test_process_restart_does_not_reuse_old_process_results(self):
        bridge = self.bridge()
        image = Image.new('RGB', (100, 50))
        self.reply(bridge, 'OLD PROCESS')
        bridge.words(image)
        bridge.process.poll.return_value = 1
        replacement = Mock()
        replacement.poll.return_value = None
        def restart():
            bridge.process = replacement
            self.reply(bridge, 'NEW PROCESS')
        with patch.object(bridge, 'start', side_effect=restart):
            self.assertEqual(bridge.words(image)[0].text, 'NEW PROCESS')
        self.assertEqual(replacement.stdin.write.call_count, 1)

    def test_lru_eviction_and_word_budget_bound_retention(self):
        bridge = self.bridge()
        first, second, third = [Image.new('RGB', (100, 50), color) for color in ('red', 'green', 'blue')]
        with patch('owrpc_app.native_ocr.MAX_CACHE_ENTRIES', 2), \
                patch('owrpc_app.native_ocr.MAX_CACHED_WORDS', 2):
            for image in (first, second):
                self.reply(bridge)
                bridge.words(image)
            bridge.words(first)  # Touch first, so second is the eviction candidate.
            self.reply(bridge)
            bridge.words(third)
            self.assertEqual(len(bridge.cache), 2)
            self.reply(bridge, 'REREAD')
            self.assertEqual(bridge.words(second)[0].text, 'REREAD')
            self.assertEqual(bridge.process.stdin.write.call_count, 4)
            self.reply(bridge, count=3)
            bridge.words(Image.new('RGB', (100, 50), 'yellow'))
            self.assertLessEqual(sum(map(len, bridge.cache.values())), 2)

    def test_ocr_error_is_not_cached_and_discards_previous_results(self):
        bridge = self.bridge()
        self.reply(bridge)
        bridge.words(Image.new('RGB', (100, 50), 'red'))
        bridge.lines.put(json.dumps({'error': 'OCR unavailable'}))
        with self.assertRaisesRegex(RuntimeError, 'OCR unavailable'):
            bridge.words(Image.new('RGB', (100, 50), 'blue'))
        self.assertFalse(bridge.cache)
        self.assertIsNone(bridge.process)
