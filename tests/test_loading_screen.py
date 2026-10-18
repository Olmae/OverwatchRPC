import unittest
from PIL import Image
from owrpc_app.loading_screen import loading_footer
from owrpc_app.detection import Word, detect


class LoadingScreenTests(unittest.TestCase):
    def test_footer_gate_excludes_black_and_bright_frames(self):
        self.assertTrue(loading_footer(Image.new('RGB', (1600, 900), (14, 20, 37))))
        self.assertFalse(loading_footer(Image.new('RGB', (1600, 900))))
        self.assertFalse(loading_footer(Image.new('RGB', (1600, 900), 'white')))

    def test_large_lower_map_caption_enters_loading_without_old_stats(self):
        words = [Word('LIJIANG', .72, .81, .11, .08), Word('TOWER', .84, .81, .08, .08),
                 Word('MYSTERY MADNESS', .82, .75, .1, .03)]
        result = detect(words, [], ['Lijiang Tower'])
        self.assertEqual((result.phase, result.map_name, result.mode),
                         ('map_loading', 'Lijiang Tower', 'Mystery Madness'))
        self.assertIsNone(result.kda)
        self.assertIsNone(result.elapsed)
        tiny = [Word(w.text, w.x, w.y, w.width, .015) for w in words]
        self.assertNotEqual(detect(tiny, [], ['Lijiang Tower']).phase, 'map_loading')
