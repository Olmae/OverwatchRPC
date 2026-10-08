from pathlib import Path


def recognize(settings, catalog=None, nickname=""):
    if catalog is not None:
        return recognize_frame(settings, catalog, nickname)
    """Local OCR of explicitly calibrated rectangles; never saves screenshots."""
    from PIL import ImageGrab, ImageOps
    import pytesseract
    if settings.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
    else:
        installed = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        pytesseract.pytesseract.tesseract_cmd = str(installed) if installed.exists() else "tesseract"
    result = {}
    for field in ("hero", "map", "kda"):
        if field == "kda" and not settings.kda_enabled:
            continue
        if field != "kda" and not settings.ocr_enabled:
            continue
        region = getattr(settings, f"{field}_region")
        if not region:
            continue
        x, y, w, h = region
        image = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        image = ImageOps.autocontrast(ImageOps.grayscale(image)).resize((w * 2, h * 2))
        result[field] = pytesseract.image_to_string(image, lang=settings.ocr_language,
                                                  config="--psm 7 -c tessedit_char_whitelist=0123456789/ " if field == "kda" else "--psm 7", timeout=3).strip()
    return result


def capture_frame(settings):
    """Capture only visible pixels of the current foreground game."""
    import ctypes
    import sys
    from PIL import ImageGrab
    from .platform import game_foreground
    if sys.platform != "win32":
        raise RuntimeError("Automatic capture currently requires Windows")
    if not game_foreground(settings.game_process):
        return None
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    from ctypes import wintypes
    rect, window = wintypes.RECT(), wintypes.RECT()
    origin = wintypes.POINT()
    if not ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)) or not ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError("Could not locate the foreground game capture area")
    if rect.right <= 0 or rect.bottom <= 0:
        return None
    image = ImageGrab.grab(window=hwnd)
    # PrintWindow includes the title bar in ordinary window mode. All OCR and
    # portrait coordinates refer to the game viewport, never the window chrome.
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(window))
    image = client_image(image, (rect.right, rect.bottom),
                         (origin.x-window.left, origin.y-window.top),
                         (window.right-window.left, window.bottom-window.top))
    if image is None:
        image = ImageGrab.grab(bbox=(origin.x, origin.y, origin.x + rect.right,
                                    origin.y + rect.bottom), all_screens=True)
    if all(high == 0 for low, high in image.convert("RGB").getextrema()):
        # PrintWindow can return black for the game's accelerated swap chain.
        # Fall back to visible client pixels, including secondary monitors.
        if hwnd != ctypes.windll.user32.GetForegroundWindow() or not game_foreground(settings.game_process):
            return None
        from ctypes import wintypes
        rect = wintypes.RECT()
        origin = wintypes.POINT()
        if not ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)) or not ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise RuntimeError("Could not locate the foreground game capture area")
        if rect.right <= 0 or rect.bottom <= 0:
            return None
        image = ImageGrab.grab(bbox=(origin.x, origin.y, origin.x + rect.right,
                                    origin.y + rect.bottom), all_screens=True)
    if hwnd != ctypes.windll.user32.GetForegroundWindow() or not game_foreground(settings.game_process):
        return None
    if all(high == 0 for low, high in image.convert("RGB").getextrema()):
        raise RuntimeError("Game capture is black; try borderless window mode")
    return image


def client_image(image, size, offset, window_size):
    """Remove verified window borders; unknown capture geometry needs fallback."""
    if image.size == size:
        return image
    x, y = offset
    width, height = size
    if image.size == window_size and x >= 0 and y >= 0 and x+width <= image.width and y+height <= image.height:
        return image.crop((x, y, x+width, y+height))
    return None


def analyze_frame(settings, catalog, nickname, image):
    """Parse a captured frame; all OCR stays on the recognition worker."""
    from .native_ocr import _engine
    import time
    started = time.monotonic()
    _engine.configure(settings.ocr_language)
    words = frame_words(image, read_names=settings.kda_enabled, nickname=settings.player_name or nickname)
    text_done = time.monotonic()
    scene = analyze_image(image, words, catalog, settings.player_name or nickname)
    from .detection import text_in
    evidence = {"hero_title": text_in(words, (.58, .29, .86, .39))[:160],
                "timer": text_in(words, (.91, .025, 1, .085))[:80],
                "text_ms": round((text_done-started)*1000, 1),
                "parse_ms": round((time.monotonic()-text_done)*1000, 1)}
    return {"__scene__": scene, "__ocr_evidence__": evidence}


def recognize_frame(settings, catalog, nickname=""):
    image = capture_frame(settings)
    return analyze_frame(settings, catalog, nickname, image) if image is not None else {}


def close_recognition():
    from .native_ocr import _engine, _latin_engine
    _engine.close()
    _latin_engine.close()


def frame_words(image, read_names=False, nickname=""):
    """Read small UI text in enlarged fixed areas, independent of its palette."""
    from PIL import ImageOps
    from .native_ocr import _engine, _latin_engine
    from .detection import Word
    words = []
    from .detection import text_in

    def read(box, upright=False, scale=3, latin=False, padded=False, shear=None):
        x1, y1, x2, y2 = box
        crop = image.crop((round(x1*image.width), round(y1*image.height),
                           round(x2*image.width), round(y2*image.height)))
        crop = ImageOps.autocontrast(ImageOps.grayscale(crop))
        if not padded:
            crop = crop.resize((crop.width*scale, crop.height*scale))
        padding = 40 if padded else 0
        if padding:
            crop = ImageOps.expand(crop, border=padding, fill=0)
        if upright:
            # Straighten Overwatch's condensed italic face before native OCR.
            slope = shear if shear is not None else (-.30 if padded else -.20)
            crop = crop.transform(crop.size, ImageOps.Image.Transform.AFFINE,
                                  (1, slope, -slope*crop.height/(2 if padded else 1), 0, 1, 0),
                                  resample=ImageOps.Image.Resampling.BICUBIC, fillcolor=0)
        if padded:
            crop = crop.resize((crop.width*scale, crop.height*scale))
        padding *= scale
        engine = _latin_engine if latin and _engine.language != "en-US" else _engine
        for w in engine.words(crop):
            inner_width, inner_height = crop.width - 2*padding, crop.height - 2*padding
            mapped = Word(w.text, x1+(w.x*crop.width-padding)/inner_width*(x2-x1),
                          y1+(w.y*crop.height-padding)/inner_height*(y2-y1),
                          w.width*crop.width/inner_width*(x2-x1),
                          w.height*crop.height/inner_height*(y2-y1))
            if not any(normalized_overlap(mapped, old) for old in words):
                words.append(mapped)
    read((0, 0, .65, .12))
    read((.65, 0, 1, .14))
    top = text_in(words, (0, 0, 1, .14))
    if 'SCOREBOARD' in top and 'RANGE' in top and 'PRACTICE RANGE' not in top:
        # The Russian OCR engine can read the English PRACTICE label as
        # IPRACTlCE. Re-read only the header in Latin before choosing table ROI.
        words[:] = [w for w in words if not (.65 < w.x < 1 and .025 < w.cy < .065)]
        read((.65, .025, 1, .065), latin=True)
        top = text_in(words, (0, 0, 1, .14))
    practice = 'УЧЕБНЫЙ ПОЛИГОН' in top or 'PRACTICE RANGE' in top
    # Avoid reading the table during menu/search screens.
    if any(t in top for t in ('SEARCHING', 'STADIUM COMPETITIVE', 'HISTORY', 'SHOP', 'BATTLE PASS')):
        return words
    from .scoreboard import locate_table
    table = locate_table(image) if any(t in top for t in ('SCOREBOARD', 'СТАТИСТИКА')) else None
    heading_box = (.32, max(.1, table.top-.005), .62, table.bottom+.005) if table else (.32, .12, .62, .4 if practice else .19)
    if table is None:
        read(heading_box, latin=practice and 'PRACTICE RANGE' in top)
    if table:
        # Column offsets follow viewport height and the observed right edge,
        # including the wider practice table and expanded perk columns.
        unit = image.height/image.width
        offset = .45 if table.top>.25 else .418
        for aliases, label, distance in ((('E','УБ'),'E',offset),
                                          (('A','СОД'),'A',offset-.05),
                                          (('D','С'),'D',offset-.10),
                                          (('DMG','УРОН'),'DMG',offset-.18),
                                          (('MIT','ПОГЛ'),'MIT',.09 if table.top>.25 else .05)):
            if not any(w.text.upper() in aliases and table.top-.01<w.cy<table.bottom+.01 for w in words):
                words.append(Word(label, table.right-distance*unit-.004, table.top,
                                  .008, table.bottom-table.top))
    heading = text_in(words, heading_box)
    if 'DMG' in heading or 'УРОН' in heading:
        geometry_headers = [w for w in words if table and table.top-.005<w.cy<table.bottom+.005]
        read((.12, .17, .6, .89))
        if table:
            words[:] = [w for w in words if not (table.left<w.x<table.right and table.top-.005<w.cy<table.bottom+.005)]
            words.extend(geometry_headers)
        compact_panel = image.width / image.height > 2
        from .portraits import scoreboard_hero
        portrait_hero = scoreboard_hero(image)
        if image.width / image.height > 2 and not practice:
            read((.815, .025, .935, .055), upright=True, scale=2, padded=True)
        if portrait_hero:
            import logging
            logging.getLogger(__name__).info('Scoreboard portrait: hero=%s', portrait_hero)
            words.append(Word(portrait_hero, .65, .345, .06, .025))
        else:
            read((.585, .33, .67, .39) if compact_panel else (.60, .33, .85, .39),
                 upright=True, scale=2, padded=True)
        if not portrait_hero and compact_panel and not text_in(words, (.585, .33, .67, .39)):
            # Short titles can disappear when the adjacent rank badge is included.
            read((.60, .335, .647, .38) if practice else (.585, .335, .635, .38),
                 upright=True, scale=1, padded=True)
        if not portrait_hero and compact_panel:
            from .catalog import load_catalog
            from .detection import catalog_name
            if catalog_name(text_in(words, (.58, .29, .86, .39)), load_catalog()['heroes'], fuzzy=True) is None:
                # A long localized title must fit in full. Keep its native size
                # instead of shrinking an enlarged panel to the OCR dimension cap.
                read((.58, .33, .85, .39), upright=True, scale=1, padded=True)
        elif not portrait_hero:
            from .catalog import load_catalog
            from .detection import catalog_name
            heroes = load_catalog()['heroes']
            title_box = (.58, .29, .86, .39)
            if catalog_name(text_in(words, title_box), heroes, fuzzy=True) is None:
                # Keep short titles separate from the rank badge. Native-size
                # Cyrillic and enlarged Latin passes cover both title alphabets.
                read((.635, .335, .715, .38), upright=True, scale=1,
                     padded=True, shear=-.20)
                if catalog_name(text_in(words, title_box), heroes, fuzzy=True) is None:
                    read((.635, .335, .715, .38), upright=True, scale=1,
                         padded=True, latin=True, shear=-.20)
                if catalog_name(text_in(words, title_box), heroes, fuzzy=True) is None:
                    read((.635, .335, .715, .38), upright=True, scale=2,
                         padded=True, latin=True, shear=-.20)
        # Long mode labels can push the map name into the timer's horizontal
        # region. Replace clock-like OCR only, keeping trailing map words.
        words[:] = [w for w in words if not (.91 < w.x < 1 and .025 < w.cy < .085
                                             and (':' in w.text or any(c.isdigit() for c in w.text)))]
        from .clock_digits import read_clock
        numeric_clock = read_clock(image)
        if numeric_clock is not None:
            words[:] = [w for w in words if not (.65<w.x<1 and .025<w.cy<.085 and ':' in w.text)]
            words.append(Word(f'{numeric_clock//60}:{numeric_clock%60:02}', .96, .03, .03, .025))
        elif practice and 'PRACTICE RANGE' in top:
            # In pillarboxed practice frames the header moves with the viewport
            # edge while the scoreboard stays centered. Anchor to RANGE instead.
            label = next((w for w in words if w.text.upper() == 'RANGE' and .025 < w.cy < .065), None)
            if label:
                left = label.x + label.width
                words[:] = [w for w in words if not (w.x > left and .025 < w.cy < .085)]
                read((left+.025, .025, min(1, left+.052), .065), upright=True,
                     scale=3, latin=True, padded=True, shear=-.20)
        elif practice and not compact_panel:
            read((.945, .025, .99, .065), scale=1, latin=True, padded=True)
            import re
            if not re.search(r'(?<!\d)\d{1,3}:[0-5]\d(?!\d)', text_in(words, (.91, .025, 1, .085))):
                read((.954, .025, .99, .065), scale=1, latin=True, padded=True)
        elif practice:
            read((.935, .025, .99, .064))
        else:
            read((.91, .025, 1, .085), upright=True, scale=1)
            read((.954, .023, 1, .064), upright=True, scale=1, latin=True)
        if read_names:
            name_left = table.column(.14) if table else .19
            name_right = table.column(.425) if table else .385
            words[:] = [w for w in words if not (name_left < w.x < name_right and .17 < w.cy < .89)]
            rows = []
            for w in sorted(words, key=lambda w: w.cy):
                if .35 < w.x < .60 and .17 < w.cy < .89 and w.text.isdigit() and not any(abs(w.cy-y)<.02 for y in rows):
                    rows.append(w.cy)
            if table and not any(abs(table.first_row-y)<.02 for y in rows):
                rows.append(table.first_row)
            elif practice:
                anchor = next((w.cy for w in words if w.text.upper() in ('УРОН', 'DMG')), None)
                if anchor is not None and not any(abs(anchor + .048-y)<.02 for y in rows):
                    rows.append(anchor + .048)
            # Own team occupies the upper table; do not OCR enemy nicknames.
            for y in rows:
                if y > (.65 if practice else .52):
                    continue
                read((name_left, max(.17,y-.025), name_right, min(.89,y+.02)), upright=True,
                     latin=any("a" <= c.lower() <= "z" for c in nickname))
    elif 'SUMMARY' in top or 'REWARDS' in top:
        pass
    else:
        read((0, .08, .47, .31))
        read((.65, .08, 1, .28))
        read((.085, .80, .23, .865))
        read((.085, .88, .25, .94))
        read((.90, .86, 1, .94))
        # Tiny ammo glyphs may be missed by native OCR. Match both separate
        # counters conservatively; their offsets follow viewport height.
        import re
        ammo = [w for w in words if w.x > .88 and w.cy > .8 and re.search(r'\d', w.text)]
        hp = [n for w in words if .07 < w.x < .23 and .8 < w.cy < .87
              for n in re.findall(r'\d{2,4}', w.text)]
        if len(hp) >= 2 and sum(len(re.findall(r'\d{1,3}', w.text)) for w in ammo) < 2:
            from .digits import read_digits
            boxes = [(image.width - round(a*image.height), round(.88*image.height),
                      image.width - round(b*image.height), round(.92*image.height))
                     for a, b in ((.12, .095), (.093, .065))]
            values = [read_digits(image.crop(box)) for box in boxes]
            if all(v is not None for v in values):
                for value, (x1, y1, x2, y2) in zip(values, boxes):
                    words.append(Word(str(value), x1/image.width, y1/image.height,
                                      (x2-x1)/image.width, (y2-y1)/image.height))
        left = text_in(words, (0, .08, .48, .31))
        right = text_in(words, (.65, .08, 1, .28))
        if not any(t in top for t in ('HEROES', 'SHOP', 'BATTLE PASS', 'ГЕРОИ', 'МАГАЗИН', 'ПОРАЖЕНИЕ', 'VICTORY', 'DEFEAT')):
            # Short transition titles otherwise lie outside the normal HUD ROIs.
            read((.32, .14, .75, .27), upright=True, scale=1, padded=True)
            if 'ГОЛОСОВ' in text_in(words, (.32, .14, .75, .27)):
                read((.93, .025, .99, .095), upright=True, scale=1, padded=True)
            if len(hp) >= 2:
                read((.3, .4, .72, .58), upright=True, scale=1, padded=True)
        if ('В МАТЧЕ' in left and 'УЧЕБНЫЙ ПОЛИГОН' in left) or 'СБОР КОМАНДЫ' in left:
            # The large condensed titles can be unreadable; the selected
            # portrait label and Continue button provide separate evidence.
            read((.42, .72, .57, .96))
            read((.83, .04, .99, .135), upright=True, scale=1, padded=True)
            if 'СБОР КОМАНДЫ' in left:
                read((.46, .83, .57, .89), upright=True, scale=1, padded=True)
        if 'SUA EQUIPE' in left and 'SELECIONAR VISUAL' in right:
            read((.07, .16, .21, .205), scale=5)
    return words


def normalized_overlap(a, b):
    return a.text.casefold() == b.text.casefold() and abs(a.x-b.x) < .008 and abs(a.cy-b.cy) < .008


def analyze_image(image, words, catalog, nickname=''):
    from dataclasses import replace
    from .detection import detect, own_row
    from .digits import read_digits
    result = detect(words, catalog['heroes'], catalog['maps'], nickname)
    if result.scene == 'scoreboard':
        from .mode_icons import scoreboard_mode
        icon_mode = scoreboard_mode(image)
        if icon_mode and result.mode in (None, 'Control', 'Escort', 'Hybrid', 'Push'):
            import logging
            logging.getLogger(__name__).info('Scoreboard mode icon: mode=%s', icon_mode)
            result = replace(result, mode=icon_mode)
    if result.phase in ('menus', 'queue'):
        from .party import party_size
        from .detection import text_in
        navigation = text_in(words, (0, 0, .8, .09))
        if any(marker in navigation for marker in ('HEROES', 'BATTLE PASS', 'SHOP', 'HISTORY', 'ГЕРОИ', 'МАГАЗИН', 'HÉROES', 'EVENTOS', 'TIENDA', 'HISTORIA')):
            result = replace(result, party_size=party_size(image))
    if result.scene != 'scoreboard' or result.kda is not None or not nickname:
        return result
    row = own_row(words, nickname)
    header_bottom = .4 if result.mode == 'Practice' else .19
    dmg = next((w for w in words if .35<w.x<.6 and .12<w.cy<header_bottom and w.text.upper() in ('DMG','УРОН')), None)
    mit = next((w for w in words if .45<w.x<.65 and .12<w.cy<header_bottom and w.text.upper() in ('MIT','ПОГЛ')), None)
    if row is None or dmg is None:
        return result
    center = dmg.x+dmg.width/2
    spacing = mit.x+mit.width/2-center if mit else dmg.width*5.3
    columns = []
    for aliases in (('E','УБ'),('A','СОД'),('D','С')):
        headers = [w for w in words if .3<w.x<.55 and .1<w.cy<header_bottom and w.text.upper() in aliases]
        if len(headers)!=1:
            columns = []
            break
        columns.append(headers[0].x+headers[0].width/2)
    if not columns:
        columns = [center-factor*spacing for factor in (1,.72,.45)]
    # Digits sit slightly below the italic nickname baseline.
    y = row.cy+.007
    values = []
    for x in columns:
        crop = image.crop((round((x-.011)*image.width),round((y-.014)*image.height),
                           round((x+.011)*image.width),round((y+.014)*image.height)))
        value = read_digits(crop)
        if value is None:
            return result
        values.append(value)
    return replace(result, kda=tuple(values))
