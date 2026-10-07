"""Conservative menu portrait-strip recognition, independent of social counters."""
from statistics import median


def portrait_tile(image, right, tile_width):
    height = image.height
    tile = image.crop((round(right-tile_width), round(height*.01),
                       round(right), round(height*.073))).resize((48, 48))
    corners = [tile.getpixel((x, y)) for x in (3, 44) for y in (3, 44)]
    background = [median(p[channel] for p in corners) for channel in range(3)]
    foreground = [max(abs(p[c]-background[c]) for c in range(3)) > 20
                  for p in tile.get_flattened_data()]
    coverage = sum(foreground) / len(foreground)
    rows = [y for y in range(48) if sum(foreground[y*48:(y+1)*48]) >= 3]
    columns = [x for x in range(48) if sum(foreground[x::48]) >= 3]
    tall = rows and (max(rows)-min(rows)+1) >= 34
    wide = columns and (max(columns)-min(columns)+1) >= 24
    return coverage >= .20 and tall and wide, coverage


def party_size(image):
    """Count contiguous profile tiles; ambiguous/hidden strips return unknown."""
    if image.width < 640 or image.height < 360:
        return None
    if image.mode != 'RGB':
        image = image.convert('RGB')
    width, height = image.size
    # Role badges can expand the first two profiles while the remaining three
    # use compact tiles. Require all five portraits and an empty next slot.
    right = width - height / 15
    wide_tiles = [portrait_tile(image, right-i*height*.0704, height*.065)[0] for i in range(2)]
    compact_tiles = [portrait_tile(image, right-2*height*.0704-i*height*.0396, height*.036)[0]
                     for i in range(4)]
    if all(wide_tiles) and all(compact_tiles[:3]) and not compact_tiles[3]:
        return 5
    count = 0
    for index in range(7):
        right = width - height / 15 - index * height * .0704
        portrait, coverage = portrait_tile(image, right, height*.065)
        # Portrait artwork spans the tile; social glyphs are small and centered.
        if portrait:
            count += 1
        elif coverage <= .18:
            return count if count else None
        else:
            return None
    return None  # Unsupported strip length; do not truncate larger groups.
