from pathlib import Path


def recognize(settings):
    """Local OCR of explicitly calibrated rectangles; never saves screenshots."""
    from PIL import ImageGrab, ImageOps
    import pytesseract
    if settings.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
    else:
        installed = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        pytesseract.pytesseract.tesseract_cmd = str(installed) if installed.exists() else "tesseract"
    result = {}
    for field in ("hero", "map"):
        region = getattr(settings, f"{field}_region")
        if not region:
            continue
        x, y, w, h = region
        image = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        image = ImageOps.autocontrast(ImageOps.grayscale(image)).resize((w * 2, h * 2))
        result[field] = pytesseract.image_to_string(image, lang=settings.ocr_language,
                                                  config="--psm 7", timeout=3).strip()
    return result
