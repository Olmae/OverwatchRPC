"""Run real Windows OCR on an external, private screenshot fixture corpus."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from PIL import Image, ImageOps
    from owrpc_app.native_ocr import _engine
    from owrpc_app.ocr import frame_words, analyze_image, close_recognition
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    corpus = json.loads(args.manifest.read_text(encoding='utf-8'))
    catalog = json.loads((ROOT/'assets/catalog.json').read_text(encoding='utf-8'))
    results = []
    try:
        for case in corpus:
            image = Image.open(args.manifest.parent/case['file']).convert('RGB')
            variant = case.get('variant')
            if variant == 'gray':
                image = ImageOps.grayscale(image).convert('RGB')
            elif variant == 'invert':
                image = ImageOps.invert(image)
            elif variant == 'hue':
                h,s,v = image.convert('HSV').split()
                h = h.point(lambda x: (x+85)%256)
                image = Image.merge('HSV', (h,s,v)).convert('RGB')
            _engine.configure(case.get('language','eng'))
            start = time.monotonic()
            words = frame_words(image, read_names=bool(case.get('nickname')), nickname=case.get('nickname',''))
            result = asdict(analyze_image(image, words, catalog, case.get('nickname','')))
            mismatch = {k:{'expected':v,'actual':result[k]} for k,v in case['expected'].items()
                        if (list(result[k]) if isinstance(result[k],tuple) else result[k]) != v}
            results.append({'file':case['file'],'variant':variant,'result':result,
                            'reference':case.get('reference',{}),'known_limitations':case.get('known_limitations',[]),
                            'seconds':round(time.monotonic()-start,3),'mismatch':mismatch, 'words':[asdict(w) for w in words] if mismatch else []})
            print(case['file'],variant,'FAIL' if mismatch else 'OK',flush=True)
    finally:
        close_recognition()
        args.report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(r['mismatch'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
