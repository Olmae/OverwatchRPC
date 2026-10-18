"""Run real Windows OCR on an external, private screenshot fixture corpus."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def select_cases(corpus, patterns):
    if not patterns:
        return corpus
    return [case for case in corpus if any(pattern.casefold() in
            (str(case.get('source_file', case['file'])) + ' ' + str(case.get('variant', ''))).casefold()
            for pattern in patterns)]


def snapshot_cases(corpus, base, folder):
    """Freeze every input before OCR starts; variants share identical pixels."""
    folder.mkdir(parents=True, exist_ok=True)
    result = []
    for original in corpus:
        case = dict(original)
        case.pop('_input_error', None)
        source = base / case['file']
        case.setdefault('source_file', str(source.resolve()))
        try:
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            target = folder / (digest + source.suffix.lower())
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                target.write_bytes(data)
            case.update(file=str(target.resolve()), sha256=digest)
        except OSError as exc:
            case['_input_error'] = str(exc)
        result.append(case)
    (folder / 'cases.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def check_case(case, base, catalog):
    from PIL import Image, ImageOps
    from owrpc_app.native_ocr import _engine
    from owrpc_app.ocr import frame_words, analyze_image
    start = time.monotonic()
    row = {'file': case['file'], 'source_file': case.get('source_file', case['file']),
           'variant': case.get('variant'), 'reference': case.get('reference', {}),
           'known_limitations': case.get('known_limitations', [])}
    try:
        if case.get('_input_error'):
            raise OSError(case['_input_error'])
        with Image.open(base / case['file']) as source:
            image = source.convert('RGB')
        variant = case.get('variant')
        if variant == 'gray':
            image = ImageOps.grayscale(image).convert('RGB')
        elif variant == 'invert':
            image = ImageOps.invert(image)
        elif variant == 'hue':
            h, s, v = image.convert('HSV').split()
            h = h.point(lambda x: (x+85)%256)
            image = Image.merge('HSV', (h, s, v)).convert('RGB')
        elif variant:
            raise ValueError(f'Unknown image variant: {variant}')
        _engine.configure(case.get('language', 'eng'))
        words = frame_words(image, read_names=bool(case.get('nickname')), nickname=case.get('nickname', ''))
        result = asdict(analyze_image(image, words, catalog, case.get('nickname', '')))
        expected = case.get('expected', {})
        mismatch = {k: {'expected': v, 'actual': result[k]} for k, v in expected.items()
                    if (list(result[k]) if isinstance(result[k], tuple) else result[k]) != v}
        status = 'FAIL' if mismatch else 'OK' if expected else 'REVIEW'
        row.update(result=result, mismatch=mismatch, status=status,
                   words=[asdict(w) for w in words] if status != 'OK' else [])
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        row.update(status='ERROR', error=f'{type(exc).__name__}: {exc}',
                   mismatch={'input_or_ocr': {'expected': 'readable case', 'actual': str(exc)}}, words=[])
    row['seconds'] = round(time.monotonic()-start, 3)
    return row


def save_report(path, results):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    from owrpc_app.ocr import close_recognition
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--snapshot-dir', type=Path, help='Copy all selected source images before running OCR')
    parser.add_argument('--filter', action='append', default=[], help='Case-insensitive source path/variant substring; repeat for OR')
    args = parser.parse_args()
    corpus = select_cases(json.loads(args.manifest.read_text(encoding='utf-8')), args.filter)
    if not corpus:
        parser.error('No matching cases; nothing was tested')
    if args.snapshot_dir:
        corpus = snapshot_cases(corpus, args.manifest.parent, args.snapshot_dir)
    catalog = json.loads((ROOT/'assets/catalog.json').read_text(encoding='utf-8'))
    results = []
    try:
        for case in corpus:
            row = check_case(case, args.manifest.parent, catalog)
            results.append(row)
            save_report(args.report, results)
            print(row['source_file'], row['variant'], row['status'], flush=True)
    finally:
        close_recognition()
        save_report(args.report, results)
    counts = {status: sum(row['status'] == status for row in results) for status in ('OK', 'FAIL', 'ERROR', 'REVIEW')}
    print(f"Cases: {len(results)}/{len(corpus)}; " + '; '.join(f'{k}: {v}' for k, v in counts.items()), flush=True)
    if counts['FAIL'] or counts['ERROR']:
        raise SystemExit(1)
    if counts['REVIEW']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
