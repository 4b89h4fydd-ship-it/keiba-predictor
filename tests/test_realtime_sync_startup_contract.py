"""Verify Realtime Sync health checks fail closed on worker exit or timeout."""
from pathlib import Path

WORKFLOW = Path(".github/workflows/arvexq-sync.yml")


def test_health_gate_allows_cold_start_without_silently_skipping_health():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "for i in $(seq 1 90)" in text
    assert 'curl -fsS --max-time 2 http://127.0.0.1:8000/health' in text
    assert "ARVEXQ live runtime ready attempt=$i" in text


def test_runtime_early_exit_and_timeout_leave_diagnostic_logs():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'kill -0 "$(cat /tmp/arvexq-live.pid)"' in text
    assert "ARVEXQ live runtime exited before /health became ready" in text
    assert "ARVEXQ live runtime /health readiness timed out" in text
    assert text.count("tail -n 120 /tmp/arvexq-live.log") == 2
    assert "exit 1" in text
