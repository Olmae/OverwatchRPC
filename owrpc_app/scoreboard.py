"""Locate the scoreboard's neutral header independently of its language."""
from dataclasses import dataclass
from PIL import ImageOps


@dataclass(frozen=True)
class Table:
    left: float
    top: float
    right: float
    bottom: float

    def column(self, fraction):
        return self.left + fraction * (self.right-self.left)

    @property
    def first_row(self):
        return self.bottom + .032


def locate_table(image):
    # A long, bright horizontal band survives grayscale and team color changes.
    # Work at a bounded resolution; text gaps are bridged only within the band.
    gray = ImageOps.grayscale(image).resize((640, 360))
    pixels = tuple(gray.get_flattened_data())
    candidates = []
    for y in range(36, 144):
        line = [value >= 175 for value in pixels[y*640:(y+1)*640]]
        start = end = None
        gap = 0
        for x, bright in enumerate(line+[False]*11):
            if bright:
                if start is None:
                    start = x
                end, gap = x+1, 0
            elif start is not None:
                gap += 1
                if gap > 10:
                    width = end-start
                    if 175 <= width <= 365 and 65 <= start <= 210 and 300 <= end <= 440:
                        coverage = sum(line[start:end])/width
                        if coverage >= .80:
                            candidates.append((y, start, end))
                    start = end = None
    bands = []
    for y, left, right in candidates:
        if bands and y == bands[-1][-1][0]+1 and abs(left-bands[-1][-1][1]) <= 4 and abs(right-bands[-1][-1][2]) <= 4:
            bands[-1].append((y,left,right))
        else:
            bands.append([(y,left,right)])
    valid = [b for b in bands if 5 <= len(b) <= 15]
    if len(valid) != 1:
        return None
    band = valid[0]
    return Table(sum(b[1] for b in band)/len(band)/640, band[0][0]/360,
                 sum(b[2] for b in band)/len(band)/640, (band[-1][0]+1)/360)
