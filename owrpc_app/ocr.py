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


def analyze_frame(settings, catalog, nickname, image, tab_sample=False, record=True):
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
                "hero_source": 'hud_icons' if scene.scene == 'hud' and scene.hero else 'text_or_portrait',
                "interface_ocr_language": _interface_ocr_language or settings.ocr_language,
                "timer": text_in(words, (.91, .025, 1, .085))[:80],
                "text_ms": round((text_done-started)*1000, 1),
                "parse_ms": round((time.monotonic()-text_done)*1000, 1)}
    from .recognition_diagnostics import recorder
    if record:
        recorder.save(image, scene, settings, evidence, tab_sample=tab_sample)
    return {"__scene__": scene, "__ocr_evidence__": evidence}


def recognize_frame(settings, catalog, nickname=""):
    image = capture_frame(settings)
    return analyze_frame(settings, catalog, nickname, image) if image is not None else {}


_interface_ocr_language = None


def escape_menu_layout(image):
    """Cheap OCR trigger only: three neutral button interiors, never a scene verdict."""
    for y in (.37, .43, .54):
        crop = image.crop((round(.60*image.width), round((y-.006)*image.height),
                           round(.625*image.width), round((y+.006)*image.height)))
        pixels = list(crop.convert('RGB').resize((8, 4)).get_flattened_data())
        if sum(min(p) >= 180 and max(p)-min(p) < 45 for p in pixels) < 26:
            return False
    return True


def interface_language(words):
    """Require multiple fixed interface labels, never player names or chat."""
    from .detection import text_in, normalize
    from difflib import SequenceMatcher
    header = text_in(words, (0, 0, .35, .09))
    for language, labels in (
        ('rus', ('ГЕРОИ', 'СОБЫТИЯ', 'БОЕВОЙ ПРОПУСК', 'МАГАЗИН')),
        ('eng', ('HEROES', 'EVENTS', 'BATTLE PASS', 'SHOP')),
    ):
        if sum(label in header for label in labels) >= 2:
            return language
    if 'СТАТИСТИКА' in header and 'ГЕРО' in header:
        return 'rus'
    if 'SCOREBOARD' in header and 'HERO INFO' in header:
        return 'eng'
    left = text_in(words, (0, .08, .48, .31))
    right = text_in(words, (.65, .08, 1, .29))
    skin_tokens = right.split()
    skin_label = any(SequenceMatcher(None, normalize(' '.join(skin_tokens[i:i+count])), 'selectskin').ratio() >= .8
                     for i in range(len(skin_tokens)) for count in (1, 2))
    if (skin_label and any(t in left for t in ('SEMBLE YOUR TEAM', 'SELECT A HERO', 'SELECT YOUR HERO'))):
        return 'eng'
    if 'В МАТЧЕ' in left and 'УЧЕБНЫЙ ПОЛИГОН' in left:
        return 'rus'
    if 'СБОР КОМАНД' in left and 'ОБЛИК' in right:
        return 'rus'
    if 'PRACTICE RANGE' in left and 'IN MATCH' in left:
        return 'eng'
    menu = text_in(words, (.44, .27, .66, .59))
    if all(label in menu for label in ('МЕНЮ', 'ПРОФИЛЬ', 'НАСТРОЙКИ')):
        return 'rus'
    if 'MENU' in menu and 'PROFILE' in menu and any(label in menu for label in ('OPTIONS', 'SETTINGS')):
        return 'eng'
    vote_title = text_in(words, (.4, .12, .6, .19))
    vote_hint = text_in(words, (.32, .19, .75, .25))
    russian_vote_hint = all(label in vote_hint for label in ('БОЛЬШЕ', 'ГОЛОСОВ', 'ПОЛЯ', 'ВЕРОЯТНОСТЬ', 'ВЫБРАНО'))
    if ('ГОЛОС' in vote_title and 'БОЛЬШЕ' in vote_hint and 'ГОЛОСОВ' in vote_hint) or russian_vote_hint:
        return 'rus'
    if 'VOTE' in vote_title and 'MAP' in vote_title and 'VOTES' in vote_hint and 'CHANCE' in vote_hint:
        return 'eng'
    return None


def nickname_language(nickname):
    import re
    return 'rus' if re.search('[А-Яа-яЁё]', nickname) else 'eng'


def close_recognition():
    global _interface_ocr_language
    from .native_ocr import _engine, _latin_engine, _russian_engine
    _engine.close()
    _latin_engine.close()
    _russian_engine.close()
    _interface_ocr_language = None


def frame_words(image, read_names=False, nickname=""):
    """Read small UI text in enlarged fixed areas, independent of its palette."""
    from PIL import ImageOps
    from .native_ocr import _engine, _latin_engine, _russian_engine
    from .detection import Word
    global _interface_ocr_language
    _russian_engine.configure('rus')
    automatic = _engine.language in ('en-US', 'ru-RU')
    primary_engine = ({'rus': _russian_engine, 'eng': _latin_engine}.get(_interface_ocr_language, _engine)
                      if automatic else _engine)
    words = []
    from .detection import text_in

    def read(box, upright=False, scale=3, latin=False, padded=False, shear=None, white=False, orange=False, russian=False):
        x1, y1, x2, y2 = box
        crop = image.crop((round(x1*image.width), round(y1*image.height),
                           round(x2*image.width), round(y2*image.height)))
        if orange:
            rgb = crop.convert('RGB')
            crop = rgb.convert('L')
            crop.putdata([255 if r > 180 and 45 < g < 190 and b < 130 and r > g*1.3 else 0
                          for r, g, b in rgb.get_flattened_data()])
        elif white:
            rgb = crop.convert('RGB')
            crop = ImageOps.grayscale(rgb)
            crop.putdata([255 if min(pixel)>160 and max(pixel)-min(pixel)<50 else 0
                          for pixel in rgb.get_flattened_data()])
        else:
            crop = ImageOps.autocontrast(ImageOps.grayscale(crop))
        if not padded:
            crop = crop.resize((round(crop.width*scale), round(crop.height*scale)))
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
            crop = crop.resize((round(crop.width*scale), round(crop.height*scale)))
        padding *= scale
        engine = _latin_engine if latin else primary_engine
        if russian:
            _russian_engine.configure('rus')
            engine = _russian_engine
        for w in engine.words(crop):
            inner_width, inner_height = crop.width - 2*padding, crop.height - 2*padding
            mapped = Word(w.text, x1+(w.x*crop.width-padding)/inner_width*(x2-x1),
                          y1+(w.y*crop.height-padding)/inner_height*(y2-y1),
                          w.width*crop.width/inner_width*(x2-x1),
                          w.height*crop.height/inner_height*(y2-y1))
            if not any(normalized_overlap(mapped, old) for old in words):
                words.append(mapped)

    def read_name(box, **options):
        # The user's name can use a different alphabet from the game's UI.
        language = nickname_language(nickname)
        read(box, latin=language == 'eng', russian=language == 'rus', **options)
    read((0, 0, .65, .12))
    read((.65, 0, 1, .14))
    escape_controls = escape_menu_layout(image)
    if escape_controls:
        read((.44, .27, .66, .59), scale=1)
        read((.44, .72, .66, .80), scale=2)
    from .queue_banner import queue_banner
    warmup_queue = queue_banner(image, words)
    if warmup_queue:
        mode, box = warmup_queue
        words.append(Word('SEARCHING', box[0], box[1], .03, .02))
        words.append(Word(mode.upper(), box[0], box[1], .03, .02))
        return words
    from .loading_screen import loading_footer
    if loading_footer(image):
        read((.70, .80, .93, .90), upright=True, scale=.5, padded=True, shear=-.20, white=True)
        read((.80, .74, .94, .81), upright=True, scale=.5, padded=True, shear=-.20, orange=True)
        from .catalog import load_catalog
        from .detection import loading_map
        if loading_map(words, load_catalog()['maps']):
            return words
    top = text_in(words, (0, 0, 1, .14))
    language = interface_language(words) if automatic else None
    if automatic and language is None:
        # Probe the other alphabet in interface-only bounds. A single label
        # or words outside this header cannot change the game OCR language.
        before = len(words)
        try:
            read((0, 0, .35, .09), scale=2, russian=primary_engine.language == 'en-US',
                 latin=primary_engine.language != 'en-US')
            language = interface_language(words[before:])
            if language is None and escape_controls:
                read((.44, .27, .66, .59), scale=1, russian=primary_engine.language == 'en-US',
                     latin=primary_engine.language != 'en-US')
                read((.44, .72, .66, .80), scale=2, russian=primary_engine.language == 'en-US',
                     latin=primary_engine.language != 'en-US')
                language = interface_language(words[before:])
            if language is None:
                read((0, .08, .47, .31), scale=3, russian=primary_engine.language == 'en-US',
                     latin=primary_engine.language != 'en-US')
                read((.65, .08, 1, .28), scale=3, russian=primary_engine.language == 'en-US',
                     latin=primary_engine.language != 'en-US')
                language = interface_language(words[before:])
            if language is None:
                read((.32, .12, .75, .25), scale=2, russian=primary_engine.language == 'en-US',
                     latin=primary_engine.language != 'en-US')
                language = interface_language(words[before:])
            if language is None:
                del words[before:]
        except RuntimeError:
            del words[before:]
    if language:
        if _interface_ocr_language != language:
            import logging
            logging.getLogger(__name__).info('Game OCR language detected: %s', language)
        _interface_ocr_language = language
        primary_engine = _russian_engine if language == 'rus' else _latin_engine
        # Re-read the search banner with the detected language before menu
        # early-return; the surrounding navigation is not queue evidence.
        read((.40, 0, .61, .20), scale=2)
        read((.025, .245, .40, .29), scale=2)
    top = text_in(words, (0, 0, 1, .14))
    if 'SCOREBOARD' in top and 'RANGE' in top and 'PRACTICE RANGE' not in top:
        # The Russian OCR engine can read the English PRACTICE label as
        # IPRACTlCE. Re-read only the header in Latin before choosing table ROI.
        words[:] = [w for w in words if not (.65 < w.x < 1 and .025 < w.cy < .065)]
        read((.65, .025, 1, .065), latin=True)
        top = text_in(words, (0, 0, 1, .14))
    practice = 'УЧЕБНЫЙ ПОЛИГОН' in top or 'PRACTICE RANGE' in top
    if 'SEARCHING' in top:
        # The expanded queue type sits below the navigation/header OCR crop.
        read((.40, .10, .61, .15), scale=2, latin=True)
        # The collapsed header only says SEARCHING. Its actual playlist is
        # printed beneath the left heading, outside the header/navigation ROI.
        read((.025, .245, .40, .29), scale=2, latin=True)
    # Avoid reading the table during menu/search screens.
    if any(t in top for t in ('SEARCHING', 'STADIUM COMPETITIVE', 'HISTORY', 'SHOP', 'BATTLE PASS', 'ГЕРОИ', 'МАГАЗИН')):
        return words
    from .scoreboard import locate_table
    table = locate_table(image)
    if table and not any(t in top for t in ('SCOREBOARD', 'СТАТИСТИКА')):
        # Other screens can contain a pale band too. Require a real statistic
        # heading before using geometry when the Tab caption is missing.
        read((table.left, table.top, table.right, table.bottom), latin=True, scale=2)
        if not any(w.text.upper() in ('DMG', 'УРОН') and table.top-.005 < w.cy < table.bottom+.005
                   for w in words):
            table = None
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
        # Only friendly statistics are needed; enemy rows add OCR work.
        numeric_left = table.right-offset*unit-.014 if table else .32
        read((numeric_left, .17, .6, .65 if practice else .52))
        if table:
            words[:] = [w for w in words if not (table.left<w.x<table.right and table.top-.005<w.cy<table.bottom+.005)]
            words.extend(geometry_headers)
        compact_panel = image.width / image.height > 2
        from .portraits import scoreboard_hero
        portrait_hero = scoreboard_hero(image)
        if image.width / image.height > 2 and not practice:
            read((.815, .025, .935, .055), upright=True, scale=2, padded=True)
            from .catalog import load_catalog
            from .detection import catalog_name
            if catalog_name(text_in(words, (.65, 0, 1, .09)), load_catalog()['maps'], fuzzy=True) is None:
                # Keep dim compact map captions at native size; enlarging a
                # long header can merge the map with the adjacent TIME label.
                russian_header = 'СТАТИСТИКА' in top
                read((.88 if russian_header else .925, .025, .948, .065),
                     scale=2, padded=True, russian=russian_header, latin=not russian_header)
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
            if table:
                # Single zeros and comma-separated totals may all be missed.
                # The neutral header still anchors every friendly row.
                step = .0667 if table.top > .25 else .0611
                for index in range(5):
                    center = table.first_row + index*step
                    if not any(abs(center-y)<.02 for y in rows):
                        rows.append(center)
            elif practice:
                anchor = next((w.cy for w in words if w.text.upper() in ('УРОН', 'DMG')), None)
                if anchor is not None and not any(abs(anchor + .048-y)<.02 for y in rows):
                    rows.append(anchor + .048)
            # Own team occupies the upper table; do not OCR enemy nicknames.
            for y in rows:
                if y > (.65 if practice else .52):
                    continue
                read_name((name_left, max(.17,y-.025), name_right, min(.89,y+.02)), upright=True)
            from .detection import own_row
            if own_row(words, nickname) is None:
                # Tight italic nameplates sometimes need native-size padding.
                for y in rows:
                    if y <= (.65 if practice else .52):
                        read_name((name_left, max(.17,y-.025), name_right, min(.89,y+.02)),
                                  upright=True, scale=1, padded=True, shear=-.20)
    elif 'SUMMARY' in top or 'REWARDS' in top:
        pass
    else:
        read((0, .08, .47, .31))
        read((.65, .08, 1, .28))
        read((.085, .80, .23, .865))
        if nickname:
            read_name((.085, .88, .25, .94))
        else:
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
        if nickname and len(hp) >= 2:
            from .hud_icons import own_hud
            if not own_hud(words, nickname):
                read_name((.05, .875, .24, .945), upright=True,
                          scale=2, padded=True, shear=-.20)
        right = text_in(words, (.65, .08, 1, .28))
        if not any(t in top for t in ('HEROES', 'SHOP', 'BATTLE PASS', 'ГЕРОИ', 'МАГАЗИН', 'ПОРАЖЕНИЕ', 'VICTORY', 'DEFEAT')):
            # Short transition titles otherwise lie outside the normal HUD ROIs.
            read((.32, .14, .75, .27), upright=True, scale=1, padded=True)
            vote_title = text_in(words, (.4, .12, .6, .19))
            if any(token in vote_title for token in ('VOTE', 'SELECTING')):
                read((.39, .205, .64, .233), latin=True, scale=2, white=True)
            if 'ГОЛОСОВ' in text_in(words, (.32, .14, .75, .27)):
                read((.93, .025, .99, .095), upright=True, scale=1, padded=True)
            read((.3, .4, .72, .58), upright=True, scale=1, padded=True,
                 shear=-.20 if primary_engine.language == 'en-US' else -.30)
            if len(hp) < 2:
                read((.84, .92, 1, .995), scale=1, latin=True, padded=True)
                # Post-match lineups and highlight playback keep this footer.
                read((.44, .945, .56, .995), scale=2, latin=True)
        if 'PLAY' in left or 'PIW' in left:
            words[:] = [w for w in words if not (.02 < w.x < .23 and .15 < w.cy < .25)]
            read((.02, .15, .23, .25), upright=True, scale=1, padded=True, latin=True, shear=-.20)
        if (('В МАТЧЕ' in left and 'УЧЕБНЫЙ ПОЛИГОН' in left)
                or ('IN MATCH' in left and 'PRACTICE RANGE' in left) or 'СБОР КОМАНДЫ' in left):
            # The large condensed titles can be unreadable; the selected
            # portrait label and Continue button provide separate evidence.
            read((.42, .72, .57, .96))
            read((.83, .04, .99, .135), upright=True, scale=1, padded=True)
            if 'СБОР КОМАНДЫ' in left:
                read((.46, .83, .57, .89), upright=True, scale=1, padded=True)
        if ('TEAM' in left or 'СБОР КОМАНДЫ' in left
                or ('УЧЕБНЫЙ ПОЛИГОН' in left and ('В МАТЧЕ' in left or 'ВЫБЕРИТЕ' in left))
                or ('PRACTICE RANGE' in left and ('IN MATCH' in left or 'SELECT' in left))):
            # Only the highlighted grid card has a name label; it can be in
            # any role column, independently of the large model's skin.
            read((.15, .76, .85, .87), scale=2, upright=True, padded=True, shear=-.20)
            if primary_engine.language != 'ru-RU':
                read((.46, .88, .54, .945), scale=2)
            read((.42, .72, .57, .82), scale=1, upright=True, padded=True)
            if primary_engine.language != 'ru-RU':
                read((.03, .235, .21, .268), scale=2, white=True)
            # The small map caption needs separation from the hero artwork.
            if primary_engine.language != 'ru-RU':
                read((.44, .88, .56, .945), scale=1, upright=True, padded=True, shear=-.20)
            from .catalog import load_catalog
            from .detection import catalog_name
            if catalog_name(text_in(words, (0, .16, .3, .21)), load_catalog()['maps']) is None:
                read((.04, .17, .30, .205), scale=2, white=True)
            from .portraits import assembly_layout
            layout = assembly_layout(image, words)
            if nickname and layout:
                wide = image.width/image.height > 2
                for center in layout[0]:
                    read_name((center-(.04 if wide else .05), .62 if wide else .635,
                          center+(.04 if wide else .05), .66 if wide else .68),
                         scale=2 if wide else 1,
                         upright=True, padded=True, shear=-.20)
                from .portraits import assembly_owner
                if wide and assembly_owner(image, words, nickname) is None:
                    compact = layout[1][0] > .47
                    for center in layout[0]:
                        read_name((center-.05, .615 if compact else .635, center+.05, .67 if compact else .68),
                                  scale=2 if compact else 1, upright=True, padded=True, shear=-.20)
                    if compact and assembly_owner(image, words, nickname) is None:
                        # Tight nameplates exclude the animated portrait glow
                        # without weakening nickname ownership verification.
                        for center in layout[0]:
                            read_name((center-.025, .625, center+.020, .65),
                                 scale=2, upright=True, padded=True, shear=-.20)
        if 'SUA EQUIPE' in left and 'SELECIONAR VISUAL' in right:
            read((.07, .16, .21, .205), scale=5)
    return words


def normalized_overlap(a, b):
    return a.text.casefold() == b.text.casefold() and abs(a.x-b.x) < .008 and abs(a.cy-b.cy) < .008


def read_counter_crop(crop):
    """Use a separate OCR observation when a digit shape is ambiguous."""
    from PIL import ImageOps
    from .native_ocr import _engine
    from .digits import read_digits
    import re
    value = read_digits(crop)
    if value is not None:
        return value
    # A tiny isolated counter can be missed in the whole numeric table. Keep
    # the shape thresholds unchanged and require one complete numeric token.
    prepared = ImageOps.expand(ImageOps.autocontrast(ImageOps.grayscale(crop)), border=16, fill=0)
    prepared = prepared.resize((prepared.width*2, prepared.height*2))
    words = _engine.words(prepared)
    if len(words) == 1 and re.fullmatch(r'[0-9]{1,3}', words[0].text):
        return int(words[0].text)
    return None


def analyze_image(image, words, catalog, nickname=''):
    from dataclasses import replace
    from .detection import detect, own_row
    result = detect(words, catalog['heroes'], catalog['maps'], nickname)
    if (result.scene == 'hud' or result.phase is None) and result.hero is None:
        from .hud_icons import hud_hero, own_hud
        if own_hud(words, nickname):
            hero = hud_hero(image)
            if hero and any(item['name'] == hero for item in catalog['heroes']):
                result = replace(result, phase='match', scene='hud', hero=hero)
    if result.scene == 'hero_select':
        from .portraits import assembly_hero
        hero = assembly_hero(image, words, nickname)
        if hero and any(item['name'] == hero for item in catalog['heroes']):
            result = replace(result, hero=hero)
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
        if any(marker in navigation for marker in ('HEROES', 'BATTLE PASS', 'SHOP', 'HISTORY', 'ГЕРОИ', 'МАГАЗИН', 'HÉROES', 'EVENTOS', 'TIENDA', 'HISTORIA', 'BACK', 'НАЗАД')):
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
    columns, stat_headers = [], []
    for aliases in (('E','УБ'),('A','СОД'),('D','С')):
        headers = [w for w in words if .3<w.x<.55 and .1<w.cy<header_bottom and w.text.upper() in aliases]
        if len(headers)!=1:
            columns = []
            break
        columns.append(headers[0].x+headers[0].width/2)
        stat_headers.append(headers[0])
    if not columns:
        stat_headers = []
        columns = [center-factor*spacing for factor in (1,.72,.45)]
    # Digits sit slightly below the italic nickname baseline.
    y = row.cy+.007
    values = []
    for index, x in enumerate(columns):
        # Keep independently verified OCR columns. A digit-template miss in
        # one already-readable counter must not discard the other counters.
        from .detection import own_stat
        native_value = own_stat(words, stat_headers, stat_headers[index], row) if stat_headers else None
        if native_value is not None:
            values.append(native_value)
            continue
        crop = image.crop((round((x-.011)*image.width),round((y-.014)*image.height),
                           round((x+.011)*image.width),round((y+.014)*image.height)))
        value = read_counter_crop(crop)
        if value is None:
            return result
        values.append(value)
    return replace(result, kda=tuple(values))
