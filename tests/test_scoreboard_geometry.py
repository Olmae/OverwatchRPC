from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageOps
from owrpc_app.scoreboard import locate_table
from owrpc_app.clock_digits import read_clock, digit


class ScoreboardGeometryTests(unittest.TestCase):
    def test_table_band_with_header_text_and_both_aspects(self):
        for size, bounds in [((3440,1440),(.251,.146,.569,.174)),
                             ((1584,891),(.147,.286,.611,.317))]:
            image = Image.new('RGB', size, '#102030')
            draw = ImageDraw.Draw(image)
            left,top,right,bottom = [round(v*size[i%2]) for i,v in enumerate(bounds)]
            draw.rectangle((left,top,right,bottom), fill='#d7dbe0')
            for x in range(left+size[0]//8,right-10,50):
                draw.rectangle((x,top+6,x+7,bottom-6), fill='#102030')
            for variant in (image, ImageOps.grayscale(image)):
                table = locate_table(variant)
                self.assertIsNotNone(table)
                self.assertAlmostEqual(table.left,bounds[0],delta=.004)
                self.assertAlmostEqual(table.right,bounds[2],delta=.004)
                self.assertAlmostEqual(table.first_row,bounds[3]+.032,delta=.004)

    def test_no_band_and_ambiguous_bands_are_rejected(self):
        image = Image.new('RGB',(1600,900),'#102030')
        self.assertIsNone(locate_table(image))
        draw = ImageDraw.Draw(image)
        for y in (140,270):
            draw.rectangle((400,y,930,y+24),fill='#dddddd')
        self.assertIsNone(locate_table(image))

    def test_real_numeric_clock_headers_and_changed_hue(self):
        # 42 is held out from template extraction. 29 covers the previously
        # unreadable zero; its 9 glyph is also a calibration asset.
        root = Path(__file__).parent/'fixtures'/'clock'
        for name, seconds in [('torbjorn-42',42),('dmon-29',29),('dva-123',123)]:
            with Image.open(root/f'{name}.png') as header:
                frame = Image.new('RGB',(3440,1440),'#101525')
                frame.paste(header,(round(3440*.65),round(1440*.025)))
                self.assertEqual(read_clock(frame),seconds)
                r,g,b = frame.split()
                self.assertEqual(read_clock(Image.merge('RGB',(g,b,r))),seconds)
                if seconds==42:
                    self.assertEqual(read_clock(ImageOps.grayscale(frame)),seconds)

    def test_shapes_and_empty_header_are_not_clock_digits(self):
        frame = Image.new('RGB',(1920,1080),'#101525')
        self.assertIsNone(read_clock(frame))
        square = Image.new('L',(20,32),255)
        self.assertIsNone(digit(square))

    def test_unreadable_minute_prefix_cannot_be_silently_dropped(self):
        root = Path(__file__).parent.parent/'assets'/'clock-digits'
        def load(label):
            with Image.open(root/f'{label}.png') as source:
                return source.copy()
        colon = Image.new('L',(6,27))
        draw = ImageDraw.Draw(colon)
        draw.rectangle((0,0,5,5),fill=255)
        draw.rectangle((0,21,5,26),fill=255)
        for prefix in ([Image.new('L',(16,32),255)],
                       [load('1'),load('0'),load('0')]):
            glyphs = prefix+[load('0'),colon,load('4'),load('2')]
            parts, x = [], 100
            for glyph in glyphs:
                parts.append((x,0,glyph))
                x += glyph.width+3
            with patch('owrpc_app.clock_digits.clock_parts',return_value=parts):
                self.assertIsNone(read_clock(Image.new('RGB',(3440,1440))))
