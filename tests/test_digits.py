from pathlib import Path
import unittest
from PIL import Image, ImageOps
from owrpc_app.digits import read_digits


class DigitTests(unittest.TestCase):
    def test_held_out_scoreboard_cells_and_inverted_colors(self):
        root = Path(__file__).parent/'fixtures'
        for value in (29,36,8):
            with Image.open(root/f'count-{value}.png') as image:
                self.assertEqual(read_digits(image), value)
                self.assertEqual(read_digits(ImageOps.invert(image.convert('RGB'))), value)
                self.assertEqual(read_digits(ImageOps.grayscale(image)), value)

    def test_background_is_not_zero(self):
        self.assertIsNone(read_digits(Image.new('RGB',(40,30),(40,150,180))))

    def test_unrecognizable_shape_is_rejected(self):
        from PIL import ImageDraw
        image = Image.new('L',(40,30),0)
        ImageDraw.Draw(image).rectangle((10,4,30,26),fill=255)
        self.assertIsNone(read_digits(image))
