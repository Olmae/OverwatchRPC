import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from owrpc_app.detection import Detection
from scripts.check_recognition import check_case, main, select_cases, snapshot_cases


class RecognitionRunnerTests(unittest.TestCase):
    def test_snapshot_survives_deleted_sources_and_deduplicates_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'frame.png'
            Image.new('RGB', (20, 20), 'blue').save(source)
            cases = [{'file': source.name, 'expected': {'phase': 'menus'}},
                     {'file': source.name, 'variant': 'gray', 'expected': {'phase': 'menus'}}]
            frozen = snapshot_cases(cases, root, root/'snapshot')
            source.unlink()
            self.assertEqual(frozen[0]['file'], frozen[1]['file'])
            self.assertEqual(frozen[0]['sha256'], frozen[1]['sha256'])
            self.assertEqual(frozen[0]['source_file'], str(source.resolve()))
            with Image.open(frozen[0]['file']) as image:
                self.assertEqual(image.size, (20, 20))
            self.assertEqual(cases[0]['file'], 'frame.png')
            self.assertEqual(json.loads((root/'snapshot/cases.json').read_text()), frozen)

    def test_missing_snapshot_input_is_explicit_and_other_frames_are_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('RGB', (20, 20)).save(root/'good.png')
            result = snapshot_cases([{'file': 'missing.png'}, {'file': 'good.png'}], root, root/'snapshot')
            self.assertIn('_input_error', result[0])
            self.assertTrue(Path(result[1]['file']).exists())
            row = check_case(result[0], root, {})
            self.assertEqual(row['status'], 'ERROR')
            self.assertTrue(row['mismatch'])

    def test_filter_uses_original_name_after_snapshot_and_never_matches_everything_accidentally(self):
        cases = [{'file': 'hash.png', 'source_file': 'Mei-tab.png', 'variant': 'gray'},
                 {'file': 'mauga-hud.png'}]
        self.assertEqual(select_cases(cases, ['MEI']), cases[:1])
        self.assertEqual(select_cases(cases, ['gray', 'mauga']), cases)
        self.assertEqual(select_cases(cases, ['missing']), [])

    def test_cli_finishes_good_cases_after_missing_file_and_does_not_pass_unlabelled_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('RGB', (20, 20)).save(root/'good.png')
            manifest = root/'cases.json'
            manifest.write_text(json.dumps([
                {'file': 'missing.png', 'expected': {'phase': 'menus'}},
                {'file': 'good.png', 'expected': {'phase': 'menus'}},
                {'file': 'good.png', 'expected': {}},
            ]))
            report = root/'reports/result.json'
            with patch('sys.argv', ['check_recognition.py', str(manifest), '--report', str(report)]), \
                    patch('owrpc_app.native_ocr._engine.configure'), \
                    patch('owrpc_app.ocr.frame_words', return_value=[]), \
                    patch('owrpc_app.ocr.analyze_image', return_value=Detection(phase='menus', scene='menus')), \
                    patch('owrpc_app.ocr.close_recognition'), patch('builtins.print'), \
                    self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(raised.exception.code, 1)
            rows = json.loads(report.read_text())
            self.assertEqual([row['status'] for row in rows], ['ERROR', 'OK', 'REVIEW'])
            self.assertTrue(rows[0]['error'])

    def test_cli_empty_filter_is_not_a_successful_test_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'cases.json'
            manifest.write_text('[{"file":"one.png"}]')
            with patch('sys.argv', ['check_recognition.py', str(manifest), '--report', str(root/'report.json'),
                                   '--filter', 'unmatched']), patch('sys.stderr'), \
                    patch('scripts.check_recognition.check_case') as analyze, \
                    self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(raised.exception.code, 2)
            analyze.assert_not_called()
