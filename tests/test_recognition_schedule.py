import unittest

from owrpc_app.recognition_schedule import RecognitionSchedule


class RecognitionScheduleTests(unittest.TestCase):
    def test_tab_bypasses_interval_and_hold_has_one_followup(self):
        schedule = RecognitionSchedule()
        self.assertTrue(schedule.due(0, True, False, 60))
        schedule.completed(1, 60)
        self.assertTrue(schedule.due(2, True, True, 60))
        schedule.completed(3, 60)
        self.assertFalse(schedule.due(3.2, True, True, 60))
        self.assertTrue(schedule.due(3.4, True, True, 60))
        schedule.completed(4, 60)
        self.assertFalse(schedule.due(5, True, True, 60))
        self.assertFalse(schedule.due(6, True, False, 60))
        self.assertTrue(schedule.due(7, True, True, 60))

    def test_release_or_background_cancels_followup(self):
        for active, tab in ((True, False), (False, True)):
            schedule = RecognitionSchedule()
            self.assertTrue(schedule.due(0, True, True, 60))
            schedule.completed(1, 60)
            self.assertFalse(schedule.due(2, active, tab, 60))
            self.assertFalse(schedule.due(3, True, False, 60))

    def test_failure_has_cooldown_even_with_new_tab_press(self):
        schedule = RecognitionSchedule()
        self.assertTrue(schedule.due(0, True, True, 60))
        schedule.failed(1)
        self.assertFalse(schedule.due(2, True, False, 60))
        self.assertFalse(schedule.due(3, True, True, 60))
        self.assertTrue(schedule.due(31, True, True, 60))
