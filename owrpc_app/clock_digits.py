"""Conservative numeric clock recognition, separate from text OCR."""
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageOps


def clock_parts(image, saturated=True):
    width, height = image.size
    crop = image.crop((round(width*.65), round(height*.025), width, round(height*.065))).convert('RGB')
    mask = Image.new('L', crop.size)
    mask.putdata([255 if max(p)>(160 if saturated else 90) and (not saturated or max(p)-min(p)>65) else 0
                  for p in crop.get_flattened_data()])
    mask = ImageOps.expand(mask, border=(20, 0), fill=0)
    mask = mask.transform(mask.size, Image.Transform.AFFINE,
                          (1, -.22, .11*mask.height, 0, 1, 0),
                          resample=Image.Resampling.NEAREST)
    columns = [bool(mask.crop((x, 0, x+1, mask.height)).getbbox()) for x in range(mask.width)]
    parts, start = [], None
    for x, active in enumerate(columns+[False]):
        if active and start is None:
            start = x
        elif not active and start is not None:
            piece = mask.crop((start, 0, x, mask.height))
            bounds = piece.getbbox()
            if bounds and bounds[3]-bounds[1] >= height*.008:
                parts.append((start, bounds[1], piece.crop(bounds)))
            start = None
    return parts


@lru_cache(maxsize=1)
def templates():
    root = Path(__file__).resolve().parent.parent/'assets'/'clock-digits'
    return {p.stem: tuple(Image.open(p).convert('L').get_flattened_data()) for p in root.glob('*.png')}


def digit(image):
    pixels = tuple(image.resize((16, 32), Image.Resampling.NEAREST).get_flattened_data())
    by_digit = {}
    for name, template in templates().items():
        label = name.split('-')[0]
        score = sum(a!=b for a,b in zip(pixels, template))/len(pixels)
        by_digit[label] = min(score, by_digit.get(label, 1))
    scores = sorted((score, label) for label, score in by_digit.items())
    if len(scores)<2 or scores[0][0]>.20 or scores[1][0]-scores[0][0]<.035:
        return None
    return scores[0][1]


def is_colon(image):
    if not .14 < image.width/image.height < .32:
        return False
    rows = [any(image.getpixel((x,y)) for x in range(image.width)) for y in range(image.height)]
    return sum(on and (i==0 or not rows[i-1]) for i,on in enumerate(rows)) == 2


def read_clock(image):
    # A saturated pass locates the normal orange clock. The second pass supports
    # bright monochrome clocks, retaining the same shape and spacing checks.
    readings = set()
    for saturated in (True, False):
        parts = clock_parts(image, saturated)
        for i, (x, y, colon) in enumerate(parts):
            if not is_colon(colon) or i<1 or i+2>=len(parts):
                continue
            seconds = parts[i+1:i+3]
            if i+3<len(parts) and parts[i+3][0]-seconds[-1][0] < image.height*.025:
                continue
            minute_parts = []
            for part in reversed(parts[:i]):
                following = minute_parts[-1][0] if minute_parts else x
                if following-part[0]-part[2].width > image.height*.015:
                    break
                if is_colon(part[2]):
                    break
                minute_parts.append(part)
                if digit(part[2]) is None or len(minute_parts)==4:
                    break
            group = list(reversed(minute_parts))+seconds
            if not 1<=len(minute_parts)<=3 or any(not .017<g.height/image.height<.03 for _,_,g in group):
                continue
            if max(g.height for _,_,g in group)-min(g.height for _,_,g in group)>image.height*.004:
                continue
            if any(b[0]-a[0]-a[2].width > image.height*.015 for a,b in zip(parts[i:i+2], seconds)):
                continue
            labels = [digit(g) for _,_,g in group]
            if any(label is None for label in labels):
                continue
            minutes, seconds_value = int(''.join(labels[:-2])), int(''.join(labels[-2:]))
            if seconds_value<60:
                readings.add(minutes*60+seconds_value)
        if readings:
            return readings.pop() if len(readings)==1 else None
    return readings.pop() if len(readings)==1 else None
