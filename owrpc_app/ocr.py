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


def recognize_frame(settings, catalog, nickname=""):
    """Capture only the foreground game window and parse native OCR word bounds."""
    import ctypes
    import sys
    from PIL import ImageGrab
    from .platform import game_foreground
    if sys.platform != "win32":
        raise RuntimeError("Automatic capture currently requires Windows")
    if not game_foreground(settings.game_process):
        return {}
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    image = ImageGrab.grab(window=hwnd)
    if hwnd != ctypes.windll.user32.GetForegroundWindow() or not game_foreground(settings.game_process):
        return {}
    from .native_ocr import _engine
    _engine.configure(settings.ocr_language)
    words = frame_words(image, read_names=settings.kda_enabled, nickname=settings.player_name or nickname)
    scene = analyze_image(image, words, catalog, settings.player_name or nickname)
    return {"__scene__": scene}


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

    def read(box, upright=False, scale=3, latin=False):
        x1, y1, x2, y2 = box
        crop = image.crop((round(x1*image.width), round(y1*image.height),
                           round(x2*image.width), round(y2*image.height)))
        crop = ImageOps.autocontrast(ImageOps.grayscale(crop))
        crop = crop.resize((crop.width*scale, crop.height*scale))
        if upright:
            # Straighten Overwatch's condensed italic face before native OCR.
            crop = crop.transform(crop.size, ImageOps.Image.Transform.AFFINE,
                                  (1, -.20, .20*crop.height, 0, 1, 0),
                                  resample=ImageOps.Image.Resampling.BICUBIC, fillcolor=0)
        engine = _latin_engine if latin and _engine.language != "en-US" else _engine
        for w in engine.words(crop):
            mapped = Word(w.text, x1+w.x*(x2-x1), y1+w.y*(y2-y1),
                          w.width*(x2-x1), w.height*(y2-y1))
            if not any(normalized_overlap(mapped, old) for old in words):
                words.append(mapped)
    read((0, 0, .65, .12))
    read((.65, 0, 1, .14))
    top = text_in(words, (0, 0, 1, .14))
    # Avoid reading the table during menu/search screens.
    if any(t in top for t in ('SEARCHING', 'STADIUM COMPETITIVE', 'HISTORY', 'SHOP', 'BATTLE PASS')):
        return words
    read((.32, .12, .62, .19))
    heading = text_in(words, (.32, .12, .62, .19))
    if 'DMG' in heading or 'УРОН' in heading:
        read((.12, .17, .6, .89))
        read((.58, .32, .85, .39), upright=True)
        words[:] = [w for w in words if not (.91 < w.x < 1 and .025 < w.cy < .085)]
        read((.91, .025, 1, .085), upright=True, scale=1)
        read((.954, .023, 1, .064), upright=True, scale=1, latin=True)
        if read_names:
            words[:] = [w for w in words if not (.19 < w.x < .36 and .17 < w.cy < .89)]
            rows = []
            for w in sorted(words, key=lambda w: w.cy):
                if .35 < w.x < .60 and .17 < w.cy < .89 and w.text.isdigit() and not any(abs(w.cy-y)<.02 for y in rows):
                    rows.append(w.cy)
            for y in rows:
                read((.19, max(.17,y-.025), .36, min(.89,y+.02)), upright=True,
                     latin=any("a" <= c.lower() <= "z" for c in nickname))
    elif 'SUMMARY' in top or 'REWARDS' in top:
        pass
    else:
        read((0, .08, .47, .31))
        read((.65, .08, 1, .28))
        read((.085, .80, .23, .865))
        read((.085, .88, .25, .94))
        read((.90, .86, 1, .94))
        left = text_in(words, (0, .08, .48, .31))
        right = text_in(words, (.65, .08, 1, .28))
        if 'SUA EQUIPE' in left and 'SELECIONAR VISUAL' in right:
            read((.07, .16, .21, .205), scale=5)
    return words


def normalized_overlap(a, b):
    return a.text == b.text and abs(a.x-b.x) < .008 and abs(a.cy-b.cy) < .008


def analyze_image(image, words, catalog, nickname=''):
    from dataclasses import replace
    from .detection import detect, own_row
    from .digits import read_digits
    result = detect(words, catalog['heroes'], catalog['maps'], nickname)
    if result.phase in ('menus', 'queue'):
        from .party import party_size
        from .detection import text_in
        navigation = text_in(words, (0, 0, .8, .09))
        if any(marker in navigation for marker in ('HEROES', 'BATTLE PASS', 'SHOP', 'HISTORY', 'ГЕРОИ', 'МАГАЗИН', 'HÉROES', 'EVENTOS', 'TIENDA', 'HISTORIA')):
            result = replace(result, party_size=party_size(image))
    if result.scene != 'scoreboard' or result.kda is not None or not nickname:
        return result
    row = own_row(words, nickname)
    dmg = next((w for w in words if .35<w.x<.6 and .12<w.cy<.19 and w.text.upper() in ('DMG','УРОН')), None)
    mit = next((w for w in words if .45<w.x<.65 and .12<w.cy<.19 and w.text.upper() in ('MIT','ПОГЛ')), None)
    if row is None or dmg is None:
        return result
    center = dmg.x+dmg.width/2
    spacing = mit.x+mit.width/2-center if mit else dmg.width*5.3
    # Digits sit slightly below the italic nickname baseline.
    y = row.cy+.007
    values = []
    for factor in (1, .72, .45):
        x = center-factor*spacing
        crop = image.crop((round((x-.011)*image.width),round((y-.014)*image.height),
                           round((x+.011)*image.width),round((y+.014)*image.height)))
        value = read_digits(crop)
        if value is None:
            return result
        values.append(value)
    return replace(result, kda=tuple(values))
