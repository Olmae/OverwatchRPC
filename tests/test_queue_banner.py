import unittest
from PIL import Image, ImageDraw
from owrpc_app.detection import Word
from owrpc_app.queue_banner import queue_banner


class QueueBannerTests(unittest.TestCase):
    def test_both_corners_need_green_banner_and_queue_label(self):
        for left in (0, 1-.43*900/1600):
            image = Image.new('RGB', (1600, 900))
            ImageDraw.Draw(image).rectangle((left*1600, 0, (left+.43*900/1600)*1600, 70), fill=(0, 190, 0))
            words = [Word('5V5:', left+.03, .025, .02, .02),
                     Word('MYSTERY MADNESS', left+.06, .025, .10, .02)]
            self.assertEqual(queue_banner(image, words)[0], 'Mystery Madness')
            self.assertIsNone(queue_banner(Image.new('RGB', image.size), words))
            self.assertIsNone(queue_banner(image, [Word('OLMAEUWU', left+.04, .025, .10, .02)]))

    def test_mode_name_in_green_environment_without_queue_evidence_is_rejected(self):
        image = Image.new('RGB', (1600, 900), (0, 190, 0))
        self.assertIsNone(queue_banner(image, [Word('MYSTERY MADNESS', .04, .025, .1, .02)]))
