import unittest
from unittest.mock import patch

from owrpc_app.model import Settings
from owrpc_app.tab_capture import Sample, TabCapture


class TabCaptureTests(unittest.TestCase):
    def setUp(self):
        self.capture = TabCapture()
        self.capture.configure(Settings(), 4, False)

    def step(self, now, pressed=True, foreground=True):
        with patch('owrpc_app.tab_capture.game_foreground', return_value=foreground), \
                patch('owrpc_app.tab_capture.tab_pressed', return_value=pressed), \
                patch('owrpc_app.tab_capture.capture_frame', return_value=object()) as grab, \
                patch('owrpc_app.tab_capture.time.monotonic', return_value=now):
            self.capture.step(now)
        return grab.call_count

    def test_short_tab_keeps_two_independent_frames_after_release(self):
        self.assertEqual(self.step(0), 0)
        self.assertEqual(self.step(.2), 1)
        self.assertEqual(self.step(.45), 1)
        self.assertEqual(self.step(.5, pressed=False), 0)
        first = self.capture.take(4, 1)
        second = self.capture.take(4, 1)
        self.assertIsNot(first.image, second.image)
        self.assertEqual(first.burst, second.burst)
        self.assertIsNone(self.capture.take(4, 1))

    def test_hold_is_bounded_and_new_tab_replaces_old_samples(self):
        for now in (0, .2, .45, .7, 1, 5, 30):
            self.step(now)
        self.assertEqual(len(self.capture.samples), 3)
        self.step(31, pressed=False)
        self.step(32)
        self.assertEqual(len(self.capture.samples), 0)

    def test_background_and_manual_revision_clear_samples(self):
        self.step(0)
        self.step(.2)
        self.step(.3, foreground=False)
        self.assertIsNone(self.capture.take(4, .3))
        self.step(1)
        self.step(1.2)
        self.capture.configure(Settings(), 5, False)
        self.assertIsNone(self.capture.take(5, 1.3))

    def test_old_or_wrong_revision_samples_are_not_used(self):
        self.capture.samples.extend([Sample(object(), 3, 1, 0, 0),
                                     Sample(object(), 4, 1, 0, 0)])
        self.assertIsNone(self.capture.take(4, 11))
