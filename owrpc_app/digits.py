"""Small scoreboard digit templates, with background and color removed."""
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageOps


def glyphs(image):
    gray = ImageOps.grayscale(image)
    values = list(gray.get_flattened_data())
    border = [gray.getpixel((x, y)) for x in range(gray.width) for y in (0, gray.height-1)]
    border += [gray.getpixel((x, y)) for y in range(gray.height) for x in (0, gray.width-1)]
    background = sorted(border)[len(border)//2]
    differences = [abs(v-background) for v in values]
    peak = max(differences, default=0)
    if peak < 40:
        return []
    mask = Image.new('L', gray.size)
    mask.putdata([255 if v > max(35, peak*.5) else 0 for v in differences])
    columns = [any(mask.getpixel((x,y)) for y in range(mask.height)) for x in range(mask.width)]
    runs, start = [], None
    for x, active in enumerate(columns+[False]):
        if active and start is None:
            start = x
        elif not active and start is not None:
            crop = mask.crop((start, 0, x, mask.height))
            bbox = crop.getbbox()
            if bbox and bbox[3]-bbox[1] >= gray.height*.25 and x-start >= 2:
                runs.append(crop.crop(bbox).resize((12,20), Image.Resampling.NEAREST))
            start = None
    return runs


@lru_cache(maxsize=1)
def templates():
    root = Path(__file__).resolve().parent.parent/'assets'/'digits'
    return {str(i): list(Image.open(root/f'{i}.png').convert('L').get_flattened_data()) for i in range(10)}


def read_digits(image):
    result = ''
    for glyph in glyphs(image):
        values = list(glyph.get_flattened_data())
        scores = sorted((sum(a!=b for a,b in zip(values, pixels))/len(values), digit)
                        for digit,pixels in templates().items())
        if scores[0][0] > .28 or scores[1][0]-scores[0][0] < .035:
            return None
        result += scores[0][1]
    return int(result) if result and len(result) <= 3 else None
