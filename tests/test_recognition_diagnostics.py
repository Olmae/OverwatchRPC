from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from owrpc_app.detection import Detection
from owrpc_app.model import Settings
from owrpc_app.recognition_diagnostics import FailureRecorder, missing_fields


class FailureRecorderTests(unittest.TestCase):
    def test_explicit_snapshot_works_with_recording_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = FailureRecorder(Path(tmp))
            path = recorder.save(Image.new('RGB', (80, 50)), Detection(), Settings(), {}, manual=True)
            self.assertTrue(path.exists())
            metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
            self.assertTrue(metadata['manual'])
            self.assertNotIn('nickname', metadata['detection'])

    def test_diagnostics_distinguish_capture_from_confirmation_and_missing_values(self):
        from owrpc_app.recognition_diagnostics import diagnostic_text
        from owrpc_app.model import Status
        snapshot = dict(read_at=100, confirmed_at=None, scene='scoreboard', missing=['kda'],
                        pending=False, duration_ms=123.4, status=Status(hero='Ana', kda=(1, 2, 3)))
        value = diagnostic_text(snapshot)
        self.assertIn('Confirmed: —', value)
        self.assertIn('Not read: E/A/D', value)
        self.assertIn('E/A/D: 1/2/3', value)
        self.assertIn('123 ms', value)
        snapshot['pending'] = True
        self.assertIn('Ожидание второго кадра', diagnostic_text(snapshot, 'ru'))

    def test_minute_snapshots_include_normal_hud_with_global_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = FailureRecorder(Path(tmp))
            settings = Settings(recognition_diagnostics=True, recognition_minute_snapshots=True)
            image = Image.new('RGB', (80, 50))
            for now, scene in ((100, 'hud'), (130, 'unknown'), (160, 'hud')):
                with patch('owrpc_app.recognition_diagnostics.time.monotonic', return_value=now):
                    recorder.save(image, Detection(scene=scene), settings, {})
            self.assertEqual(len(list(Path(tmp).glob('*.png'))), 2)
            for path in Path(tmp).glob('*.json'):
                self.assertTrue(json.loads(path.read_text())['periodic'])

    def test_only_missing_expected_fields_trigger_evidence(self):
        settings = Settings(kda_enabled=True, player_name='Own player')
        complete = Detection(scene='scoreboard', hero='Ana', map_name='Nepal',
                             mode='Control', kda=(1, 2, 3), elapsed=60)
        self.assertEqual(missing_fields(complete, settings), [])
        complete = replace(complete, kda=None)
        self.assertEqual(missing_fields(complete, settings), ['kda'])
        settings.kda_enabled = False
        self.assertEqual(missing_fields(complete, settings), [])
        self.assertEqual(missing_fields(Detection(), settings), [])
        self.assertEqual(missing_fields(Detection(), settings, tab_sample=True), ['scene'])

    def test_opt_in_rate_limit_retention_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'failures'
            recorder = FailureRecorder(folder, max_frames=2)
            image = Image.new('RGB', (80, 50))
            scene = Detection(scene='scoreboard', nickname='Private player')
            settings = Settings()
            recorder.save(image, scene, settings, {})
            self.assertFalse(folder.exists())
            settings.recognition_diagnostics = True
            with patch('owrpc_app.recognition_diagnostics.time.monotonic', return_value=100):
                recorder.save(image, scene, settings, {})
                recorder.save(image, scene, settings, {})
            self.assertEqual(len(list(folder.glob('*.png'))), 1)
            for now in (161, 222):
                with patch('owrpc_app.recognition_diagnostics.time.monotonic', return_value=now):
                    recorder.save(image, scene, settings, {})
            self.assertEqual(len(list(folder.glob('*.png'))), 2)
            self.assertEqual(len(list(folder.glob('*.json'))), 2)
            metadata = json.loads(next(folder.glob('*.json')).read_text(encoding='utf-8'))
            self.assertNotIn('nickname', metadata['detection'])
            self.assertIn('elapsed', metadata['missing'])

    def test_periodic_frames_do_not_evict_readable_failure_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            recorder = FailureRecorder(folder, max_frames=2)
            settings = Settings(recognition_diagnostics=True, recognition_minute_snapshots=True)
            image = Image.new('RGB', (80, 50))
            with patch('owrpc_app.recognition_diagnostics.time.monotonic', return_value=100):
                failure = recorder.save(image, Detection(scene='scoreboard'), settings, {})
            for now in (1000, 1061, 1122):
                with patch('owrpc_app.recognition_diagnostics.time.monotonic', return_value=now):
                    recorder.save(image, Detection(scene='hud'), settings, {})
            self.assertTrue(failure.exists())
            self.assertEqual(len(list(folder.glob('*.png'))), 2)
            self.assertEqual(len(list(folder.glob('*.json'))), 2)

    def test_manual_evidence_survives_new_failures_and_dropped_capture_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = FailureRecorder(Path(tmp), max_frames=1)
            settings = Settings(recognition_diagnostics=True, recognition_minute_snapshots=True)
            image = Image.new('RGB', (80, 50))
            manual = recorder.save(image, Detection(), settings, {}, manual=True)
            self.assertIsNone(recorder.save(image, Detection(scene='scoreboard'), settings, {}))
            self.assertTrue(manual.exists())

    def test_retention_tolerates_corrupt_legacy_metadata(self):
        from owrpc_app.recognition_diagnostics import retention_priority
        with tempfile.TemporaryDirectory() as tmp:
            frame = Path(tmp) / 'legacy.png'
            frame.with_suffix('.json').write_text('invalid', encoding='utf-8')
            self.assertEqual(retention_priority(frame), 0)
            frame.with_suffix('.json').write_text('[]', encoding='utf-8')
            self.assertEqual(retention_priority(frame), 0)

    def test_disk_failure_does_not_break_recognition_and_byte_cap_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = FailureRecorder(Path(tmp), max_bytes=1)
            settings = Settings(recognition_diagnostics=True)
            recorder.save(Image.new('RGB', (80, 50)), Detection(), settings, {}, tab_sample=True)
            self.assertFalse(list(Path(tmp).glob('*.png')))
            with patch('PIL.Image.Image.save', side_effect=OSError('disk full')):
                with self.assertLogs('owrpc_app.recognition_diagnostics', level='WARNING'):
                    FailureRecorder(Path(tmp)).save(Image.new('RGB', (80, 50)), Detection(),
                                                   settings, {}, tab_sample=True)
