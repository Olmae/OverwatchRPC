"""Visual fallback for known hero titles on the confirmed selection screen."""
from functools import lru_cache
from statistics import correlation

from .catalog import resource_dir

TITLES = (
    ('Ashe', 'ashe', (.925, .05, .978, .118)),
    ('Kiriko', 'kiriko', (.862, .05, .978, .118)),
)


@lru_cache(maxsize=2)
def template(key):
    from PIL import Image
    with Image.open(resource_dir() / 'assembly-titles' / (key + '.png')) as image:
        return list(image.convert('L').getdata())


def assembly_title(image):
    from PIL import ImageChops, ImageFilter
    # These title positions have been verified only on the ultrawide layout.
    if abs(image.width / image.height - 3440 / 1440) > .02:
        return None
    scores = []
    for hero, key, box in TITLES:
        crop = image.crop(tuple(round(v*s) for v, s in zip(box, image.size*2)))
        crop = crop.convert('L').resize((120, 40))
        edges = ImageChops.subtract(crop, crop.filter(ImageFilter.GaussianBlur(3)), offset=128)
        try:
            score = correlation(template(key), list(edges.getdata()))
        except (OSError, ValueError):
            continue
        scores.append((score, hero))
    scores.sort(reverse=True)
    if len(scores) == 2 and scores[0][0] >= .92 and scores[0][0]-scores[1][0] >= .20:
        return scores[0][1]
    return None
