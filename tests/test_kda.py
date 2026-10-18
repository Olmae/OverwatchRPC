import unittest
from owrpc_app.model import Settings, Status, build_payload, parse_kda, kda_is_fresh


class KdaTests(unittest.TestCase):
    def test_old_counters_keep_values_but_advertise_their_age(self):
        settings = Settings(language='ru', kda_enabled=True)
        status = Status(phase='match', hero='Ana', kda=(12, 4, 3), kda_read_at=100)
        self.assertNotIn('мин назад', build_payload(settings, status, now=219)['state'])
        self.assertIn('E/A/D 12/4/3 · 2 мин назад', build_payload(settings, status, now=220)['state'])
        self.assertIn('18 мин назад', build_payload(settings, status, now=1200)['state'])
        status.kda_read_at = 1200
        self.assertNotIn('мин назад', build_payload(settings, status, now=1201)['state'])
        self.assertEqual(status.kda, (12, 4, 3))

    def test_unknown_queue_mode_does_not_publish_previous_mode_or_empty_prefix(self):
        payload = build_payload(Settings(language='en'), Status(phase='queue', mode=''))
        self.assertEqual(payload['details'], 'In Queue')
        self.assertNotIn('Mystery Madness', str(payload))

    def test_only_three_unambiguous_numbers_are_accepted(self):
        self.assertEqual(parse_kda('12 4 3'), (12, 4, 3))
        self.assertEqual(parse_kda('12 / 4 / 3'), (12, 4, 3))
        for text in ('12 4', '12 4 3 1500', 'I2 4 3', '-1 4 3', '12.4 3', 'Ana 12 4 3', '1234 1 2'):
            self.assertIsNone(parse_kda(text), text)

    def test_last_confirmed_stats_remain_until_match_exit(self):
        settings = Settings(kda_enabled=True, ocr_interval=5)
        status = Status(phase='match', hero='Ana', started_at=50, kda=(12, 4, 3), kda_read_at=100)
        self.assertTrue(kda_is_fresh(settings, status, now=110))
        self.assertTrue(kda_is_fresh(settings, status, now=1200))
        self.assertFalse(kda_is_fresh(settings, status, now=90))
        self.assertIn('12/4/3', build_payload(settings, status, now=110)['state'])
        self.assertIn('12/4/3', build_payload(settings, status, now=1200)['state'])
        self.assertNotIn('12/4/3', build_payload(Settings(), status, now=110)['state'])
        status.transition('menus')
        self.assertIsNone(status.kda)
        self.assertIsNone(status.kda_read_at)

    def test_custom_state_is_kept_and_new_match_clears_stats(self):
        status = Status(phase='match', kda=(4, 1, 2), kda_read_at=10)
        self.assertEqual(build_payload(Settings(kda_enabled=True, state_override='My status'), status, now=11)['state'], 'My status')
        status.transition('match', now=20)
        self.assertIsNone(status.kda)
        status.kda = (4, 1, 2)
        status.kda_read_at = 21
        status.transition('match', now=22)
        self.assertEqual(status.kda, (4, 1, 2))


if __name__ == '__main__':
    unittest.main()
