#!/usr/bin/env python3
"""Serve the existing frontend against rewrite-engine payloads.

Stdlib-only HTTP server:

- ``/`` (and other paths) serve files from a static directory — point
  it at a copy of the production ``arvexq/ui/static`` tree. The
  frontend's data calls are same-shape ``/api/day`` and ``/api/race``
  responses generated here; note the production app.js hardcodes the
  production API origin, so a served copy must be origin-adjusted by
  whoever wires the test page — this server never rewrites JS.
- ``GET /api/day?date=YYYY-MM-DD`` (alias ``/api/races?date=``)
  returns the production day shape for races stored in the DB.
- ``GET /api/race/<race_id>`` runs the full pipeline for that race
  (ability -> pace -> forecast -> tickets) and returns the production
  race envelope produced by rewrite.output.api_shape.

Usage:
  python scripts/arvexq_rewrite_serve.py <db_path> <static_dir> [port]
"""
from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.output.api_shape import day_payload, race_payload  # noqa: E402

# Beta fitted on the 2026-10-21..2026-10-23 training slice only
# (time-ordered backtest selection). Probabilities served with it are
# still uncalibrated priors; EV tickets stay suppressed.
SERVE_BETA = 2.0


class Engine:
    """Loads stored races once and generates payloads on demand."""

    def __init__(self, db_path: str):
        self.store = Store(db_path)
        self.races = {race.race_id: race for race in self.store.load_races()}
        self._cache: dict[str, dict] = {}
        # Provenance is read up front: the Store connection belongs to
        # this thread, while HTTP handlers run in worker threads.
        self._provenance_by_race = {
            race_id: self._provenance(race_id) for race_id in self.races
        }

    def day(self, date: str) -> dict:
        return day_payload(date, list(self.races.values()))

    def _provenance(self, race_id: str) -> dict:
        row = self.store.db.execute(
            "SELECT snapshot_sha256 FROM normalized_races WHERE race_id=?",
            (race_id,),
        ).fetchone()
        if not row:
            return {}
        snapshot_sha = row[0]
        raw = self.store.db.execute(
            "SELECT fetched_at, body FROM raw_snapshots"
            " WHERE kind='api_race_detail' AND race_key=? AND sha256=?",
            (race_id, snapshot_sha),
        ).fetchone()
        provenance = {"snapshot_sha256": snapshot_sha}
        if raw:
            provenance["captured_at"] = raw[0]
            try:
                body = json.loads(raw[1])
            except (TypeError, ValueError):
                body = {}
            if isinstance(body, dict) and isinstance(body.get("odds"), list):
                provenance["odds"] = body["odds"]
        return provenance

    def race(self, race_id: str) -> dict | None:
        race = self.races.get(race_id)
        if race is None:
            return None
        if race_id not in self._cache:
            forecast = forecast_race(race, beta=SERVE_BETA)
            pace = forecast_pace(race)
            win_odds = {
                r.number: r.win_odds.value
                for r in race.runners
                if r.win_odds.present
                and isinstance(r.win_odds.value, (int, float))
            }
            tickets = generate_tickets(
                forecast, win_odds, calibration_validated=False
            )
            self._cache[race_id] = race_payload(
                race, forecast, pace, tickets,
                provenance=self._provenance_by_race.get(race_id) or {},
            )
        return self._cache[race_id]


def make_handler(engine: Engine, static_dir: str):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=static_dir, **kwargs)

        def log_message(self, *args):  # keep the console quiet
            pass

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (http.server API)
            parsed = urlparse(self.path)
            path = parsed.path
            if path in ("/api/day", "/api/races"):
                date = (parse_qs(parsed.query).get("date") or [""])[0]
                if not date:
                    self._json({"ok": False, "error": "date required"}, 400)
                    return
                self._json(engine.day(date))
                return
            if path.startswith("/api/race/"):
                race_id = unquote(path[len("/api/race/"):])
                payload = engine.race(race_id)
                if payload is None:
                    self._json({"ok": False, "error": "race not found"}, 404)
                    return
                self._json(payload)
                return
            if path.startswith("/api/"):
                self._json({"ok": False, "error": "not implemented"}, 404)
                return
            super().do_GET()

    return Handler


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    db_path, static_dir = sys.argv[1], sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8765
    engine = Engine(db_path)
    server = ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(engine, static_dir)
    )
    print(f"serving {static_dir} + rewrite API on http://127.0.0.1:{port} "
          f"({len(engine.races)} races, beta={SERVE_BETA})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
