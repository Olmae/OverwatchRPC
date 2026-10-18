"""Cheap loading-footer gate before reading the large lower-right map title."""


def loading_footer(image):
    crop = image.crop((0, round(image.height*.945), image.width, round(image.height*.99)))
    pixels = crop.convert('RGB').resize((64, 4)).get_flattened_data()
    return sum(5 <= r <= 40 and 10 <= g <= 45 and 20 <= b <= 65
               and b > r+5 for r, g, b in pixels) >= 64*4*.8
