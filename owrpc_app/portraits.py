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
    anchors = {round(width * x) for x in (.58, .588, .60, .608, .627)}
    anchors.add(round(width / 2 + .225 * height))
    crops = [image.crop((x, top, x + side, top + side)).convert('L')
             .resize((32, 32), Image.Resampling.LANCZOS).tobytes()
             for x in anchors if x >= 0 and x + side <= width]
    return rank_crops(crops)


def rank_crops(crops, references=None):
    scores = {}
    for name, mask, reference, reference_norm in (templates() if references is None else references):
        best = -1.
        for crop in crops:
            values = [crop[i] for i in mask]
            mean = sum(values) / len(values)
            centered = [value - mean for value in values]
            norm = sqrt(sum(value * value for value in centered))
            if norm:
                best = max(best, sum(a * b for a, b in zip(reference, centered)) / (reference_norm * norm))
        scores[name] = max(scores.get(name, -1), best)
    return sorted(((score, name) for name, score in scores.items()), reverse=True)


@lru_cache(maxsize=1)
def assembly_templates():
    # Sanitized portrait-only references from maintainer-provided captures.
    result = []
    entries = [('Ramattra', 'ramattra'), ('Ramattra', 'ramattra-highlight'),
               ('Anran', 'anran'), ('Echo', 'echo'), ('Freja', 'freja'),
               ('Doctrine', 'doctrine'), ('Lúcio', 'lucio'), ('Hazard', 'hazard'),
               ('Kiriko', 'kiriko'), ('Mei', 'mei')]
    for name, key in entries:
        filename = 'assembly-' + key + '.png'
        with Image.open(resource_dir() / filename) as source:
            pixels = source.convert('L').resize((32, 32), Image.Resampling.LANCZOS).tobytes()
        mask = tuple(y*32+x for y in range(3, 29) for x in range(3, 29))
        values = [pixels[i] for i in mask]
        mean = sum(values)/len(values)
        centered = tuple(v-mean for v in values)
        result.append((name, mask, centered, sqrt(sum(v*v for v in centered))))
    return tuple(result)


def assembly_layout(image, words):
    aspect = image.width/image.height
    if 1.70 < aspect < 1.85:
        return (.19, .345, .50, .655, .81), (.452, .455, .458), .02
    if 2.2 < aspect < 2.6:
        ready = any(w.text.upper() in ('READY', 'CONTINUE', 'ПРОДОЛЖИТЬ') and .42 < w.x < .57 and .84 < w.cy < .96
                    for w in words)
        if ready:
            return (.315, .408, .50, .592, .685), (.476, .478, .480), .015
        return (.267, .384, .50, .616, .733), (.452, .455, .458), .014
    return None


def assembly_owner(image, words, nickname):
    from difflib import SequenceMatcher
    from .detection import normalize
    layout = assembly_layout(image, words)
    if not nickname or layout is None:
        return None
    matches = []
    for word in words:
        if not .63 < word.cy < .67:
            continue
        score = SequenceMatcher(None, normalize(word.text), normalize(nickname)).ratio()
        center = word.x + word.width/2
        slot = min(layout[0], key=lambda x: abs(x-center))
        if score >= .8 and abs(slot-center) <= .035:
            matches.append((score, word, slot))
    # Multiple OCR passes can read the same physical nameplate differently.
    # Distinct matching player slots remain ambiguous and are never merged.
    if len({match[2] for match in matches}) != 1:
        return None
    return max(matches, key=lambda match: match[0])[1]


def assembly_hero(image, words, nickname):
    """Match only the nickname-verified player's assembly portrait.

    Hexagonal assembly frames obscure more of the illustration than Tab.
    Require a wider margin between heroes and abstain outside this layout.
    """
    layout = assembly_layout(image, words)
    owner = assembly_owner(image, words, nickname)
    if owner is None:
        return None
    center = owner.x + owner.width/2
    slots, tops, offset = layout
    slot = min(slots, key=lambda x: abs(x-center))
    if abs(slot-center) > .035:
        return None
    side = .10*image.height
    crops = [image.crop(((slot-offset+dx)*image.width, top*image.height,
                         (slot-offset+dx)*image.width+side, top*image.height+side))
             .convert('L').resize((32, 32), Image.Resampling.LANCZOS).tobytes()
             for dx in (-.002, 0, .002) for top in tops]
    scores = rank_crops(crops, templates() + assembly_templates())
    if len(scores) < 2 or scores[0][0] < .86 or scores[0][0]-scores[1][0] < .15:
        return None
    return scores[0][1]


def scoreboard_hero(image):
    """Abstain on unknown artwork or ambiguous matches; caller verifies Tab."""
    scores = rank_portraits(image)
    if len(scores) < 2 or scores[0][0] < .86 or scores[0][0] - scores[1][0] < .10:
        return None
    return scores[0][1]
