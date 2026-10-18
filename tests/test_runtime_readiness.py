"""Readiness must tolerate slow imports, stop on death and honor its deadline."""
import unittest
from arvexq.infra.runtime_readiness import wait_ready


class RuntimeReadinessTests(unittest.TestCase):
    def test_healthy_runtime_after_old_twenty_second_limit(self):
        now = [0.0]
        def probe(url, timeout):
            if now[0] < 25:
                raise ConnectionRefusedError("still importing")
        attempts = wait_ready("http://local/health", pid=1, timeout=60,
                              probe=probe, alive=lambda _: True,
                              clock=lambda: now[0],
                              sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertEqual(attempts, 26)
        self.assertEqual(now[0], 25)

    def test_process_exit_stops_without_an_http_request(self):
        with self.assertRaisesRegex(RuntimeError, "process exited"):
            wait_ready("http://local/health", pid=1, alive=lambda _: False,
                       probe=lambda *_: self.fail("dead process was probed"))

    def test_retry_and_request_timeouts_never_exceed_deadline(self):
        now, budgets = [0.0], []
        def probe(url, timeout):
            budgets.append(timeout)
            raise OSError("not ready")
        with self.assertRaises(TimeoutError):
            wait_ready("http://local/health", pid=1, timeout=2.5,
                       probe=probe, alive=lambda _: True, clock=lambda: now[0],
                       sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertEqual(budgets, [2, 1.5, 0.5])
        self.assertEqual(now[0], 2.5)

    def test_invalid_wait_configuration_is_rejected(self):
        for options in ({"pid": 0}, {"pid": 1, "timeout": 0},
                        {"pid": 1, "interval": 0}, {"pid": 1, "request_timeout": 0}):
            with self.assertRaises(ValueError):
                wait_ready("http://local/health", **options)


if __name__ == "__main__":
    unittest.main()
