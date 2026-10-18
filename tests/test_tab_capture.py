import unittest
from unittest.mock import patch

from owrpc_app.model import Settings
from owrpc_app.tab_capture import Sample, TabCapture


class TabCaptureTests(unittest.TestCase):
    def setUp(self):
        shortcut = patch('owrpc_app.tab_capture.diagnostic_shortcut_pressed', return_value=False)
        shortcut.start()
        self.addCleanup(shortcut.stop)
        self.capture = TabCapture()
        self.capture.configure(Settings(), 4, False)

    def test_shortcut_requires_right_alt_and_right_bracket(self):
        from owrpc_app.platform import diagnostic_shortcut_pressed
        with patch('owrpc_app.platform.sys.platform', 'win32'), \
                patch('owrpc_app.platform.ctypes.windll') as native:
            pressed = {0xA5, 0xDD}
            native.user32.GetAsyncKeyState.side_effect = lambda key: 0x8000 if key in pressed else 0
            self.assertTrue(diagnostic_shortcut_pressed())
            # AltGr may also report Ctrl. It must still work without requiring it.
            pressed.add(0x11)
            self.assertTrue(diagnostic_shortcut_pressed())
            pressed.clear()
            for keys in ({0xA4, 0xDD}, {0x11, 0xDD}, {0xA5}, {0xDD}):
                pressed.clear()
                pressed.update(keys)
                self.assertFalse(diagnostic_shortcut_pressed())

    def test_manual_shortcut_captures_once_while_held_even_when_paused(self):
        self.capture.configure(Settings(ocr_enabled=False, kda_enabled=False), 4, True)
        with patch('owrpc_app.tab_capture.diagnostic_shortcut_pressed', return_value=True):
            self.assertEqual(self.step(1, pressed=False), 1)
            self.assertEqual(self.step(4, pressed=False), 0)
        sample = self.capture.take(4, 4)
        self.assertTrue(sample.manual)
        self.assertIsNone(self.capture.take(4, 4))

    def test_tray_request_waits_for_verified_game_foreground(self):
        self.capture.request_snapshot()
        self.assertEqual(self.step(1, pressed=False, foreground=False), 0)
        self.assertEqual(self.step(2, pressed=False), 1)
        self.assertTrue(self.capture.take(4, 2).manual)


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
        self.assertEqual(len(self.capture.samples), 3)
        self.step(32.2)
        self.assertEqual(len(self.capture.samples), 1)
        self.assertEqual(self.capture.samples[0].burst, 2)

    def test_brief_repeat_does_not_cancel_captured_frames(self):
        self.step(0)
        self.step(.2)
        sample = self.capture.samples[0]
        self.step(.3, pressed=False)
        self.step(.4)
        self.step(.5, pressed=False)
        self.assertTrue(self.capture.current(sample))
        self.assertIs(self.capture.take(4, .6), sample)

    def test_safe_captured_frames_survive_focus_loss_but_not_manual_revision(self):
        self.step(0)
        self.step(.2)
        self.step(.3, foreground=False)
        self.assertIsNotNone(self.capture.take(4, .3))
        self.step(1)
        self.step(1.2)
        self.capture.configure(Settings(), 5, False)
        self.assertIsNone(self.capture.take(5, 1.3))

    def test_old_or_wrong_revision_samples_are_not_used(self):
        self.capture.samples.extend([Sample(object(), 3, 1, 0, 0),
                                     Sample(object(), 4, 1, 0, 0)])
        self.assertIsNone(self.capture.take(4, 21))
