"""Local scoreboard illustration matching; no models, OCR language or network."""
from functools import lru_cache
from math import sqrt

from PIL import Image

from .catalog import resource_dir


@lru_cache(maxsize=1)
def templates():
    import json
    folder = resource_dir() / 'tab-portraits'
    if not (folder / 'sources.json').exists():
        return ()
    entries = json.loads((folder / 'sources.json').read_text(encoding='utf-8'))
    result = []
    for entry in entries:
        with Image.open(folder / (entry['key'] + '.png')) as source:
            rgba = source.convert('RGBA').resize((32, 32), Image.Resampling.LANCZOS)
        alpha = rgba.getchannel('A').tobytes()
        pixels = rgba.convert('L').tobytes()
        # Transparent surroundings and panel edges are not hero evidence.
        mask = tuple(i for i, value in enumerate(alpha)
                     if value >= 245 and 2 <= i % 32 < 30 and 2 <= i // 32 < 30)
        if len(mask) < 250:
            continue
        values = [pixels[i] for i in mask]
        mean = sum(values) / len(values)
        centered = tuple(value - mean for value in values)
        norm = sqrt(sum(value * value for value in centered))
        if norm:
            result.append((entry['name'], mask, centered, norm))
    return tuple(result)


def rank_portraits(image):
    """Return best correlations for the bounded known scoreboard panel layouts."""
    width, height = image.size
    side, top = round(.158 * height), round(.145 * height)
    if side < 48:
        return []
    anchors = {round(width * x) for x in (.58, .588, .60, .627)}
    anchors.add(round(width / 2 + .225 * height))
    crops = [image.crop((x, top, x + side, top + side)).convert('L')
             .resize((32, 32), Image.Resampling.LANCZOS).tobytes()
             for x in anchors if x >= 0 and x + side <= width]
    scores = []
    for name, mask, reference, reference_norm in templates():
        best = -1.
        for crop in crops:
            values = [crop[i] for i in mask]
            mean = sum(values) / len(values)
            centered = [value - mean for value in values]
            norm = sqrt(sum(value * value for value in centered))
            if norm:
                best = max(best, sum(a * b for a, b in zip(reference, centered)) / (reference_norm * norm))
        scores.append((best, name))
    return sorted(scores, reverse=True)


def scoreboard_hero(image):
    """Abstain on unknown artwork or ambiguous matches; caller verifies Tab."""
    scores = rank_portraits(image)
    if len(scores) < 2 or scores[0][0] < .86 or scores[0][0] - scores[1][0] < .10:
        return None
    return scores[0][1]
