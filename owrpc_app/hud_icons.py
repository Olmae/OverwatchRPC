"""Offline matching of ready ability glyphs in the player's bottom-right HUD."""
from functools import lru_cache
import json

from PIL import Image, ImageDraw

from .catalog import resource_dir


def signature(mask):
    bounds = mask.getbbox()
    if bounds is None:
        return None
    glyph = mask.crop(bounds)
    if min(glyph.size) < 3:
        return None
    aspect = glyph.width / glyph.height
    glyph.thumbnail((28, 28), Image.Resampling.LANCZOS)
    canvas = Image.new('L', (32, 32))
    canvas.paste(glyph, ((32-glyph.width)//2, (32-glyph.height)//2))
    bits = sum(1 << i for i, value in enumerate(canvas.tobytes()) if value >= 128)
    return bits, aspect


@lru_cache(maxsize=1)
def templates():
    folder = resource_dir() / 'hud-icons'
    rows = json.loads((folder/'sources.json').read_text(encoding='utf-8'))
    result = []
    for row in rows:
        with Image.open(folder/(row['key']+'.png')) as source:
            rgba = source.convert('RGBA')
            mask = rgba.getchannel('A').point(lambda value: 255 if value >= 128 else 0)
        value = signature(mask)
        if value:
            weapon = row['key'].endswith('-0') or row['name'] in (
                'Kunai', 'Caduceus Blaster', 'Forge Hammer', 'Pummel (Nemesis Form)')
            result.append((row['hero'], row['name'], *value, weapon))
    return tuple(result)


def ability_glyphs(image):
    """Extract enclosed dark glyphs from separate neutral ready-ability tiles.

    Cooldowns, colored locked tiles and the keyboard labels are not references.
    Coordinates follow viewport height, rather than stretching with ultrawide.
    """
    height = image.height
    if height < 480 or not 1.65 < image.width/height < 2.65:
        return []
    crop = image.crop((round(image.width-.65*height), round(.78*height),
                       image.width, round(.915*height))).convert('RGB')
    scale = min(1, 600/crop.width)
    crop = crop.resize((round(crop.width*scale), round(crop.height*scale)))
    width, rows = crop.size
    white = {i for i, (r, g, b) in enumerate(crop.get_flattened_data())
             if min(r, g, b) >= 155 and max(r, g, b)-min(r, g, b) < 55}
    glyphs = []
    unit = height*scale
    while white:
        seed = white.pop()
        pending, component = [seed], [seed]
        while pending:
            point = pending.pop()
            x, y = point % width, point // width
            for nxt in ((point-1 if x else -1), (point+1 if x+1 < width else -1),
                        (point-width if y else -1), (point+width if y+1 < rows else -1)):
                if nxt in white:
                    white.remove(nxt)
                    pending.append(nxt)
                    component.append(nxt)
        xs = [p % width for p in component]
        ys = [p // width for p in component]
        left, top, right, bottom = min(xs), min(ys), max(xs)+1, max(ys)+1
        w, h = right-left, bottom-top
        if not (.025*unit < w < .095*unit and .035*unit < h < .10*unit
                and .6 < w/h < 1.8 and len(component)/(w*h) > .28):
            continue
        plate = Image.new('L', (w+2, h+2))
        pixels = plate.load()
        for point in component:
            pixels[point % width-left+1, point // width-top+1] = 255
        ImageDraw.floodfill(plate, (0, 0), 128)
        ink = plate.point(lambda value: 255 if value == 0 else 0)
        # White details inside a black glyph are isolated from the plate's
        # outer component. Preserve those holes instead of filling the logo.
        ink_pixels = ink.load()
        source_pixels = crop.load()
        for y in range(h):
            for x in range(w):
                if max(source_pixels[left+x, top+y]) >= 155:
                    ink_pixels[x+1, y+1] = 0
        value = signature(ink)
        if value:
            glyphs.append((left, top, value))
    return sorted(glyphs)


def rank_glyph(value, weapon=False):
    bits, aspect = value
    ranked = []
    for hero, name, reference, ref_aspect, is_weapon in templates():
        if weapon and not is_weapon:
            continue
        if min(aspect, ref_aspect)/max(aspect, ref_aspect) < .70:
            continue
        shifts = (-33, -32, -31, -1, 0, 1, 31, 32, 33)
        score = max(2*(bits & (reference << shift if shift >= 0 else reference >> -shift)).bit_count()
                    /(bits.bit_count()+reference.bit_count()) for shift in shifts)
        ranked.append((score, hero, name))
    return sorted(ranked, reverse=True)


def weapon_glyphs(image):
    """Alternate weapon bounds share one vote; ammo/counters are not evidence."""
    values = []
    for left, right in ((.25, .14), (.29, .18), (.26, .12), (.22, .10)):
        rgb = image.crop((image.width-left*image.height, .83*image.height,
                          image.width-right*image.height, .90*image.height)).convert('RGB')
        mask = rgb.convert('L')
        mask.putdata([255 if min(p) > 160 and max(p)-min(p) < 45 else 0
                      for p in rgb.get_flattened_data()])
        value = signature(mask)
        if value:
            values.append(value)
    return values


def match_slots(slots, weapon_slot=None, margin=.12):
    """Joint hero margin: one similar barrier cannot outweigh a unique pair."""
    candidates = {}
    for index, values in enumerate(slots):
        for value in values:
            for score, hero, name in rank_glyph(value, weapon=index == weapon_slot):
                if score >= .60:
                    key = (index, name)
                    rows = candidates.setdefault(hero, {})
                    rows[key] = max(rows.get(key, 0), score)
    ranked = []
    for hero, rows in candidates.items():
        pairs = [(min(a, b), max(a, b)) for (slot, name), a in rows.items()
                 for (other_slot, other_name), b in rows.items()
                 if slot < other_slot and name != other_name]
        if not pairs:
            continue
        low, high = max(pairs, key=lambda pair: sum(pair))
        ranked.append(((low+high)/2, low, high, hero))
    ranked.sort(reverse=True)
    if (not ranked or ranked[0][1] < .78 or ranked[0][2] < .86 or ranked[0][0] < .82
            or len(ranked) > 1 and ranked[0][0]-ranked[1][0] < margin):
        return None
    return ranked[0][3]


def hud_hero(image):
    """Require distinct ready abilities, or an ability and weapon, for one hero."""
    glyphs = ability_glyphs(image)
    if not glyphs:
        return None
    slots = [[value] for _, _, value in glyphs]
    hero = match_slots(slots)
    if hero:
        return hero
    slots.append(weapon_glyphs(image))
    hero = match_slots(slots, weapon_slot=len(slots)-1, margin=.09)
    # A weapon silhouette is less distinctive than two separate abilities.
    # It may support a unique high-confidence ability, never identify alone.
    for _, _, value in glyphs:
        ranked = rank_glyph(value)
        if ranked and ranked[0][1] == hero and ranked[0][0] >= .86:
            other = next((score for score, name, _ in ranked if name != hero), 0)
            if ranked[0][0]-other >= .12:
                return hero
    return None


def own_hud(words, nickname):
    from difflib import SequenceMatcher
    from .detection import normalize, text_in
    if not nickname:
        return False
    header = text_in(words, (0, 0, 1, .25))
    if any(t in header for t in ('SPECTATING', 'KILL CAM', 'KILLCAM', 'REPLAY', 'НАБЛЮДЕНИЕ', 'ПОВТОР',
                                'SCOREBOARD', 'СТАТИСТИКА', 'HERO INFO', 'ИНФОРМАЦИЯ О ГЕРОЕ')):
        return False
    if any(w.text.upper() in ('DMG', 'MIT', 'УРОН', 'ПОГЛ') and .30 < w.x < .65 and .1 < w.cy < .4
           for w in words):
        return False
    matches = [w for w in words if .04 < w.x < .25 and .875 < w.cy < .945
               and SequenceMatcher(None, normalize(w.text), normalize(nickname)).ratio() >= .8]
    # Repeated OCR passes on one nameplate are okay, two distinct names aren't.
    return bool(matches) and max(w.x for w in matches)-min(w.x for w in matches) < .025
