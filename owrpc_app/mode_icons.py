"""Bounded binary glyph matching for scoreboard map types."""
from functools import lru_cache

from PIL import Image

from .catalog import resource_dir


def binary_strip(image):
    height = 32
    image = image.convert('L').resize((round(image.width * height / image.height), height),
                                     Image.Resampling.LANCZOS)
    pixels = image.tobytes()
    rows = [sum(1 << x for x in range(image.width) if pixels[y * image.width + x] >= 150)
            for y in range(height)]
    return image.width, rows


@lru_cache(maxsize=1)
def templates():
    folder = resource_dir() / 'mode-icons'
    result = []
    for mode in ('Control', 'Escort', 'Hybrid', 'Push'):
        path = folder / (mode.lower() + '.png')
        if not path.exists():
            continue
        with Image.open(path) as source:
            width, rows = binary_strip(source)
        bits = sum(row << (y * width) for y, row in enumerate(rows))
        result.append((mode, width, bits))
    return tuple(result)


def rank_modes(image):
    width, height = image.size
    strip_width, rows = binary_strip(image.crop((round(.65 * width), round(.025 * height),
                                                round(.95 * width), round(.06 * height))))
    scores = []
    for mode, glyph_width, reference in templates():
        mask = (1 << glyph_width) - 1
        best = 0.
        for x in range(strip_width - glyph_width + 1):
            candidate = sum(((row >> x) & mask) << (y * glyph_width) for y, row in enumerate(rows))
            union = (candidate | reference).bit_count()
            if union:
                best = max(best, (candidate & reference).bit_count() / union)
        scores.append((best, mode))
    return sorted(scores, reverse=True)


def scoreboard_mode(image):
    scores = rank_modes(image)
    if len(scores) < 2 or scores[0][0] < .80 or scores[0][0] - scores[1][0] < .12:
        return None
    return scores[0][1]
