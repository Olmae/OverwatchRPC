"""The compact green queue banner can sit above an active warmup HUD."""
from .detection import mode_from, text_in


def queue_banner(image, words):
    width = min(.3, .43 * image.height / image.width)
    for left, right in ((0, width), (1-width, 1)):
        box = (left, .015, right, .075)
        crop = image.crop((round(left*image.width), round(.015*image.height),
                           round(right*image.width), round(.075*image.height)))
        pixels = crop.convert('RGB').resize((64, 20)).get_flattened_data()
        green = sum(g > 100 and r < g*.65 and b < g*.65 for r, g, b in pixels)
        if green < 64*20*.55:
            continue
        text = text_in(words, box)
        # A clipped leading M occurs in the compact right-hand label.
        mode = mode_from(text.replace(' YSTERY MADNESS', ' MYSTERY MADNESS'))
        if mode and ('5V5' in text or '5V5' in text.replace(' ', '')
                     or any(c.isdigit() for c in text) and ':' in text):
            return mode, box
    return None
