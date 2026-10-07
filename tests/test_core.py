import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from owrpc_app.model import Settings, Status, build_payload, match_catalog, StableMatch
from owrpc_app.storage import load_settings, save_settings
from owrpc_app.runtime import RpcSession


class ModelTests(unittest.TestCase):
    def test_payload_uses_names_and_preserves_match_start(self):
        s = Status(phase="match", hero="Ana", map_name="King's Row", started_at=42)
        p = build_payload(Settings(), s)
        self.assertIn("King's Row", p["details"])
        self.assertIn("Ana", p["state"])
        self.assertEqual(p["start"], 42)
        self.assertNotIn("small_image", p)

    def test_phase_transitions_reset_timer_only_for_new_match(self):
        s = Status()
        s.transition("match", now=10)
        s.transition("match", now=20)
        self.assertEqual(s.started_at, 10)
        s.transition("queue", now=30)
        s.transition("match", now=40)
        self.assertEqual(s.started_at, 40)

    def test_invalid_config_is_validated(self):
        s = Settings.from_dict({"rpc_interval": 1, "ocr_interval": -2,
                                "client_id": "broken", "autostart": "false",
                                "map_region": [0, 0, -1, 500]})
        self.assertEqual(s.rpc_interval, 15)
        self.assertGreaterEqual(s.ocr_interval, 3)
        self.assertEqual(s.client_id, Settings().client_id)
        self.assertFalse(s.autostart)
        self.assertIsNone(s.map_region)

    def test_ocr_matches_names_and_refuses_noise_or_short_substrings(self):
        catalog = ["Ana", "Anubis", "King's Row", "D.Va"]
        self.assertEqual(match_catalog("KING’S ROW", catalog), "King's Row")
        self.assertEqual(match_catalog("D VA", catalog), "D.Va")
        self.assertIsNone(match_catalog("banana", catalog))
        self.assertIsNone(match_catalog("???", catalog))

    def test_debounce_requires_consecutive_observations(self):
        d = StableMatch()
        self.assertIsNone(d.observe("Ana"))
        self.assertIsNone(d.observe(None))
        self.assertIsNone(d.observe("Ana"))
        self.assertEqual(d.observe("Ana"), "Ana")
        d.reset()
        self.assertIsNone(d.observe("Ana"))

    def test_menu_does_not_publish_old_hero(self):
        p = build_payload(Settings(), Status(phase="menus", hero="Ana"))
        self.assertNotIn("Ana", p.get("state", ""))

    def test_modern_assets_and_button(self):
        settings = Settings(button_label="Profile", button_url="https://example.com", display_type=2)
        p = build_payload(settings, Status(phase="match", hero="Ana", map_name="Busan"),
                          {"portrait": "https://example.com/ana.png", "source": "https://example.com/ana"},
                          {"screenshot": "https://example.com/busan.png"})
        self.assertEqual(p["small_image"], "https://example.com/ana.png")
        self.assertEqual(p["large_image"], "https://example.com/busan.png")
        self.assertEqual(p["status_display_type"], 2)
        self.assertEqual(p["buttons"][0]["label"], "Profile")

    def test_invalid_button_link_is_not_published(self):
        p = build_payload(Settings(button_label="Open", button_url="file:///secret"), Status())
        self.assertNotIn("buttons", p)


class StorageTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            save_settings(Settings(hero="Ana"), p)
            self.assertEqual(load_settings(p)[0].hero, "Ana")
            self.assertEqual(json.loads(p.read_text())["hero"], "Ana")

    def test_corrupt_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text("broken")
            settings, warning = load_settings(p)
            self.assertIsInstance(settings, Settings)
            self.assertTrue(warning)
            self.assertTrue(list(Path(d).glob("settings.corrupt-*.json")))


class FakePresence:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def connect(self):
        self.calls.append("connect")
        if self.fail:
            raise OSError("Discord closed")

    def update(self, **payload):
        self.calls.append(payload)

    def clear(self):
        self.calls.append("clear")

    def close(self):
        self.calls.append("close")


class RpcTests(unittest.TestCase):
    def test_reconnect_after_failed_connection(self):
        bad, good = FakePresence(True), FakePresence()
        clients = iter([bad, good])
        rpc = RpcSession(lambda _: next(clients))
        self.assertFalse(rpc.send("123", {"details": "Playing"}))
        self.assertTrue(rpc.send("123", {"details": "Playing"}))
        self.assertEqual(good.calls[0], "connect")

    def test_clear_does_not_connect_and_deduplicates(self):
        client = FakePresence()
        rpc = RpcSession(lambda _: client)
        rpc.send("123", None)
        self.assertEqual(client.calls, [])
        rpc.send("123", {"details": "Playing"})
        rpc.send("123", None)
        rpc.send("123", None)
        self.assertEqual(client.calls.count("clear"), 1)

    def test_app_id_change_closes_previous_connection(self):
        a, b = FakePresence(), FakePresence()
        clients = iter([a, b])
        rpc = RpcSession(lambda _: next(clients))
        rpc.send("1", {"details": "A"})
        rpc.send("2", {"details": "B"})
        self.assertIn("close", a.calls)
        self.assertIn("clear", a.calls)
        self.assertEqual(b.calls[0], "connect")

    def test_unchanged_activity_heartbeat_detects_closed_discord(self):
        client = FakePresence()
        rpc = RpcSession(lambda _: client)
        with patch("owrpc_app.runtime.time.monotonic", return_value=100):
            rpc.send("1", {"details": "A"})
        with patch("owrpc_app.runtime.time.monotonic", return_value=120):
            rpc.send("1", {"details": "A"})
        self.assertEqual(len([x for x in client.calls if isinstance(x, dict)]), 1)
        client.update = lambda **_: (_ for _ in ()).throw(OSError("Discord restarted"))
        with patch("owrpc_app.runtime.time.monotonic", return_value=161):
            self.assertFalse(rpc.send("1", {"details": "A"}))
        self.assertIsNone(rpc.client)


if __name__ == "__main__":
    unittest.main()
