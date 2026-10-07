import queue
import unittest
from unittest.mock import patch

from owrpc_app.model import Settings, Status
from owrpc_app.runtime import Worker


class Ticks:
    def __init__(self, count, callback=None):
        self.count, self.tick, self.callback = count, 0, callback

    def wait(self, _):
        self.tick += 1
        if self.callback:
            self.callback(self.tick)
        return self.tick > self.count


class FakeRpc:
    def __init__(self):
        self.calls = []

    def send(self, client_id, payload):
        self.calls.append(payload)
        return True

    def close(self):
        pass


CATALOG = {"heroes": [{"name": "Ana", "portrait": "https://example.com/ana.png"}], "maps": []}


class WorkerTests(unittest.TestCase):
    def make_worker(self, foreground=True, callback=None, status=None):
        events = queue.Queue()
        worker = Worker(Settings(ocr_enabled=True, ocr_interval=3), status or Status(phase="match"), CATALOG, events)
        worker.stop_event = Ticks(3, callback)
        rpc = FakeRpc()
        with patch("owrpc_app.runtime.RpcSession", return_value=rpc), \
                patch("owrpc_app.runtime.game_running", return_value=True), \
                patch("owrpc_app.runtime.game_foreground", return_value=foreground), \
                patch("owrpc_app.runtime.recognize", return_value={"hero": "Ana"}) as capture, \
                patch("owrpc_app.runtime.time.monotonic", side_effect=lambda: worker.stop_event.tick * 10):
            worker.run()
        results = []
        while not events.empty():
            results.append(events.get())
        return worker, rpc, capture, results

    def test_ocr_never_captures_background_window(self):
        _, _, capture, results = self.make_worker(foreground=False)
        capture.assert_not_called()
        self.assertFalse(any(e == "recognized" for e, _ in results))

    def test_ocr_never_captures_menus(self):
        _, _, capture, _ = self.make_worker(status=Status(phase="menus"))
        capture.assert_not_called()

    def test_two_samples_update_hero_and_shutdown_clears(self):
        worker, rpc, capture, results = self.make_worker()
        self.assertEqual(worker.status.hero, "Ana")
        self.assertGreaterEqual(capture.call_count, 2)
        self.assertTrue(any(e == "recognized" for e, _ in results))
        self.assertIsNone(rpc.calls[-1])


if __name__ == "__main__":
    unittest.main()
