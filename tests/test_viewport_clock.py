import unittest

from PIL import Image

from owrpc_app.model import ScoreboardClock
from owrpc_app.ocr import client_image, normalized_overlap
from owrpc_app.detection import Word, detect


class ViewportClockTests(unittest.TestCase):
    def test_overlapping_header_passes_ignore_ocr_case(self):
        words = [Word('урон', .448, .29, .023, .012),
                 Word('УРОН', .4482, .2902, .023, .012),
                 Word('ПОГЛ', .553, .29, .022, .012),
                 Word('УЧЕБНЫЙ ПОЛИГОН', .8, .03, .15, .02),
                 Word('D.MON', .643, .344, .05, .025)]
        unique = []
        for word in words:
            if not any(normalized_overlap(word, old) for old in unique):
                unique.append(word)
        result = detect(unique, ['D.Mon'], ['Practice Range'])
        self.assertEqual((result.scene, result.hero), ('scoreboard', 'D.Mon'))
        self.assertFalse(normalized_overlap(words[0], Word('УРОН', .448, .5, .023, .012)))

    def test_window_chrome_is_removed_without_resizing_game_pixels(self):
        frame = Image.new('RGB', (1602, 932), 'purple')
        frame.paste('black', (1, 31, 1601, 931))
        client = client_image(frame, (1600, 900), (1, 31), frame.size)
        self.assertEqual(client.size, (1600, 900))
        self.assertEqual(client.getextrema(), ((0, 0), (0, 0), (0, 0)))
        self.assertIs(client_image(client, client.size, (0, 0), client.size), client)
        self.assertIsNone(client_image(frame, (1600, 900), (8, 40), frame.size))

    def test_timer_requires_consistent_captures_and_uses_capture_time(self):
        clock = ScoreboardClock()
        self.assertIsNone(clock.observe(93, 1000))
        self.assertEqual(clock.observe(94, 1001), 907)
        self.assertIsNone(clock.observe(7, 1002))  # One erroneous OCR digit.
        self.assertIsNone(clock.observe(96, 1003))
        self.assertEqual(clock.observe(97, 1004), 907)
        self.assertIsNone(clock.observe(None, 1005))
        self.assertIsNone(clock.observe(98, 1006))
        self.assertIsNone(clock.observe(140, 1048))  # Stale unrelated observation.

    def test_round_clock_reset_can_sync_without_changing_match_fields(self):
        clock = ScoreboardClock()
        clock.observe(500, 1000)
        self.assertEqual(clock.observe(501, 1001), 500)
        self.assertIsNone(clock.observe(0, 1002))
        self.assertEqual(clock.observe(1, 1003), 1002)

    def test_repeated_timer_error_cannot_predate_game_launch(self):
        clock = ScoreboardClock()
        self.assertIsNone(clock.observe(45376, 10000, 6000))
        self.assertIsNone(clock.observe(45377, 10001, 6000))
        self.assertIsNone(clock.observe(3382, 10002, 6000))
        self.assertEqual(clock.observe(3383, 10003, 6000), 6620)
        self.assertIsNone(clock.observe(-1, 10004, 6000))
