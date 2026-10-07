"""Conservative menu portrait-strip recognition, independent of social counters."""
from statistics import median


def party_size(image):
    """Count contiguous profile tiles; ambiguous/hidden strips return unknown."""
    if image.width < 640 or image.height < 360:
        return None
    if image.mode != 'RGB':
        image = image.convert('RGB')
    width, height = image.size
    count = 0
    for index in range(7):
        right = width - height / 15 - index * height * .0704
        tile = image.crop((round(right-height*.065), round(height*.01),
                           round(right), round(height*.073))).resize((48, 48))
        corners = [tile.getpixel((x, y)) for x in (3, 44) for y in (3, 44)]
        background = [median(p[channel] for p in corners) for channel in range(3)]
        pixels = list(tile.get_flattened_data())
        foreground = [max(abs(p[c]-background[c]) for c in range(3)) > 20 for p in pixels]
        coverage = sum(foreground) / len(pixels)
        rows = [y for y in range(48) if sum(foreground[y*48:(y+1)*48]) >= 3]
        columns = [x for x in range(48) if sum(foreground[x::48]) >= 3]
        tall = rows and (max(rows)-min(rows)+1) >= 34
        wide = columns and (max(columns)-min(columns)+1) >= 24
        # Portrait artwork spans the tile; social glyphs are small and centered.
        if coverage >= .20 and tall and wide:
            count += 1
        elif coverage <= .18:
            return count if count else None
        else:
            return None
    return None  # Unsupported strip length; do not truncate larger groups.
