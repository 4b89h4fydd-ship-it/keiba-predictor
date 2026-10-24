"""Regression: pre-day official cards must not freeze next-day forecast products.

The workflow keeps the same API and D1 acquisition paths.  A specific cron
selects tomorrow's date and stops after verified factual card publication.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "arvexq-prefetch.yml"
)
DAY_AHEAD_SCHEDULE = "05 5,8,11 * * *"


def step_block(source: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    assert source.count(marker) == 1, f"missing or ambiguous step: {name}"
    tail = source.split(marker, 1)[1]
    return tail.split("\n      - name: ", 1)[0]


def run_date_step(source: str, requested: str, expression: str) -> dict:
    import textwrap

    body = step_block(source, "Resolve target date")
    match = re.search(r"(?m)^        run: \|\n", body)
    assert match, "date-resolution shell script absent"
    script = textwrap.dedent(body[match.end():].rstrip()) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        env.update(
            REQUESTED_DATE=requested,
            SCHEDULE_EXPRESSION=expression,
            GITHUB_ENV=str(Path(tmp) / "github.env"),
            TZ="Asia/Tokyo",
        )
        subprocess.run(["bash", "-e", "-c", script], check=True, env=env)
        entries = (Path(tmp) / "github.env").read_text()
    return dict(line.split("=", 1) for line in entries.splitlines() if "=" in line)


class PrefetchNextDayScheduleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_new_cron_is_unique(self) -> None:
        self.assertEqual(
            self.workflow.count(f'    - cron: "{DAY_AHEAD_SCHEDULE}"'), 1
        )

    def test_day_ahead_date_and_normal_schedules(self) -> None:
        before = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        tomorrow = run_date_step(self.workflow, "", DAY_AHEAD_SCHEDULE)
        today = run_date_step(self.workflow, "", "30 20 * * *")
        push = run_date_step(self.workflow, "", "")
        after = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        self.assertIn(tomorrow["TARGET_DATE"], {
            (before + timedelta(days=1)).isoformat(),
            (after + timedelta(days=1)).isoformat(),
        })
        self.assertEqual(tomorrow["ARVEXQ_DAY_AHEAD"], "1")
        for output in (today, push):
            self.assertIn(output["TARGET_DATE"], {before.isoformat(), after.isoformat()})
            self.assertNotEqual(output.get("ARVEXQ_DAY_AHEAD"), "1")

    def test_manual_date_overrides_schedule(self) -> None:
        output = run_date_step(self.workflow, "2026-11-03", DAY_AHEAD_SCHEDULE)
        self.assertEqual(output["TARGET_DATE"], "2026-11-03")
        self.assertNotEqual(output.get("ARVEXQ_DAY_AHEAD"), "1")

    def test_day_ahead_does_not_generate_prediction_products(self) -> None:
        guarded = (
            "Analyze only persisted D1 data and prepare original marks and bets",
            "Prepare previous-day research training corpus (optional)",
            "Capture optional preoff research candidates (not production picks)",
            "Report research capture operational evidence",
            "Record research capture result in progress issue",
            "Archive research-only preoff receipts",
            "Calibrate ticket hit rates from sealed previous-day results",
            "Publish empirical calibration independently of immutable morning originals",
            "Replace legacy active forecasts in D1 publication payload",
            "Freeze morning selected and special predictions for all races",
            "Publish fixed morning race list as a Cloudflare static asset",
            "Preserve lossless prediction originals before D1 writes",
            "Select only missing or thin D1 details",
            "Push prepared day repairs to D1 in safe batches",
            "Verify prepared day and analysis from D1",
            "Preserve morning D1 consistency audit",
        )
        for name in guarded:
            with self.subTest(step=name):
                self.assertIn(
                    "env.ARVEXQ_DAY_AHEAD != '1'",
                    step_block(self.workflow, name),
                )

    def test_day_ahead_keeps_existing_fact_publication(self) -> None:
        for name in (
            "Discover all officially available races",
            "Publish official day summaries before heavy prediction work",
            "Collect racecards and full careers without running predictions",
            "Publish lightweight racecards independent of D1 capacity",
            "Persist collected facts using the existing D1 sync pipeline",
            "Read D1 facts back and require identical horse/history evidence",
        ):
            with self.subTest(step=name):
                self.assertNotIn("ARVEXQ_DAY_AHEAD", step_block(self.workflow, name))


if __name__ == "__main__":
    unittest.main()
