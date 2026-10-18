"""Readiness must tolerate slow imports, stop on death and honor its deadline."""
import unittest
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from arvexq.infra.runtime_readiness import wait_ready


class RuntimeReadinessTests(unittest.TestCase):
    def test_cli_reads_health_from_an_external_working_directory(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
            def log_message(self, *_args):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                pid_file = Path(directory) / "runtime.pid"
                pid_file.write_text(str(os.getpid()))
                script = Path(__file__).resolve().parents[1] / "scripts/arvexq_wait_runtime.py"
                result = subprocess.run([
                    sys.executable, str(script), "--pid-file", str(pid_file),
                    "--url", "http://127.0.0.1:" + str(server.server_port) + "/health",
                    "--timeout", "2",
                ], cwd=directory, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("ARVEXQ_RUNTIME_READY", result.stdout)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

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
