"""M3 bias tables + features (preregistration section 6).

For every record race, each runner's residual is
    resid = expected_pct - actual_pct     (positive = ran BETTER
                                           than its v9b ability base
                                           implied)
with expected_pct from pairwise Bradley-Terry shares of p_cal.
Bias tables are per box, keyed by course = venue x surface x
distance (inner/outer split only where course_geometry.json has
exactly one verified variant) x frame (1..8) for the frame table
and x style tercile (pre-race tendency from past-run corner
positions) for the style table.  Static tables use the fit window
(dates <= 2026-08-31) with shrinkage n/(n+50); a weekly component
uses the trailing 28 days of EARLIER races at the same course only.
Output per runner: frame_static, frame_weekly, style_static,
style_weekly (bias values; 0.0 when the cell is empty).
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from rewrite.analysis.shadow_v8 import BETAS, WEIGHTS  # noqa: E402

SHRINK_K = 50.0
WEEKLY_DAYS = 28


def expected_pct(p_cal: dict) -> dict:
    out = {}
    nums = list(p_cal)
    for n in nums:
        s = 0.0
        for m in nums:
            if m != n:
                s += p_cal[m] / (p_cal[n] + p_cal[m])
        out[n] = s / (len(nums) - 1) if len(nums) > 1 else 0.5
    return out


def style_tendency(runs) -> float | None:
    vals = []
    for _d, _t, _rn, _f, fsize, corner_first in runs[:3]:
        if not corner_first or not fsize or fsize <= 1:
            continue
        vals.append(1.0 - (corner_first - 1) / (fsize - 1))
    return sum(vals) / len(vals) if vals else None


def main() -> int:
    db = common.corpus()
    nar_records, jra_records = common.load_records()
    bases, _ = common.load_primary_window()
    race_meta = {r[0]: {"date": r[1], "track": r[2], "surface": r[3],
                        "distance": r[4]}
                 for r in db.execute(
                     "SELECT race_id, race_date, track, surface, distance"
                     " FROM races")}
    frames = {}
    for rid, number, fr in db.execute(
            "SELECT race_id, number, frame FROM runners"):
        frames[(rid, int(number))] = fr
    natkey_of = {}
    for rid, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners"):
        natkey_of[(rid, int(number))] = nk
    card_runs = defaultdict(list)
    for rid, nk, rdate, track, rnum, fin, fsize, cfirst in db.execute(
            "SELECT card_race_id, owner_natkey, run_date, track,"
            " race_number, finish, field_size, corner_first"
            " FROM past_runs ORDER BY run_date DESC"):
        card_runs[(rid, nk)].append((rdate, track, rnum, fin, fsize, cfirst))

    # ---- residuals for every record race --------------------------
    rows = []  # per runner dicts
    for box, records in (("nar", nar_records), ("jra", jra_records)):
        seg = "nar" if box == "nar" else "jra_flat"
        for rec in records:
            if rec["segment"] != seg:
                continue
            status, strengths = common.base_strengths(
                rec, WEIGHTS[seg], BETAS[seg])
            if status != "ok":
                continue
            p_cal = common.pcal_from_strengths(strengths)
            exp = expected_pct(p_cal)
            meta = race_meta.get(rec["race_id"])
            if meta is None:
                continue
            finish = rec.get("finishers") or {}
            field = len(finish)
            if field < 4 or rec.get("winner") is None:
                continue
            course = (meta["track"], meta["surface"], meta["distance"])
            for n in rec["numbers"]:
                if n not in finish or n not in exp:
                    continue
                nk = natkey_of.get((rec["race_id"], n))
                style = style_tendency(card_runs.get((rec["race_id"], nk), []))
                rows.append({
                    "race_id": rec["race_id"], "date": rec["date"],
                    "box": box, "course": course, "number": n,
                    "frame": frames.get((rec["race_id"], n)),
                    "style": style,
                    "actual_pct": finish[n] / field,
                    "exp_pct": exp[n],
                    "resid": exp[n] - finish[n] / field,
                    "field": field, "surface": meta["surface"],
                    "distance": meta["distance"],
                })
    # ---- style terciles per box from the static window ------------
    terciles = {}
    for box in ("nar", "jra"):
        vals = sorted(r["style"] for r in rows
                      if r["box"] == box and r["style"] is not None
                      and r["date"] <= "2026-08-31")
        if len(vals) >= 30:
            terciles[box] = (vals[len(vals) // 3], vals[2 * len(vals) // 3])
    def tercile(box, style):
        if style is None or box not in terciles:
            return None
        lo, hi = terciles[box]
        return 0 if style <= lo else (2 if style > hi else 1)

    for r in rows:
        r["tercile"] = tercile(r["box"], r["style"])

    # ---- static tables (fit window <= 2026-08-31) -----------------
    def build_table(keyfn):
        agg = defaultdict(lambda: [0.0, 0])
        for r in rows:
            if r["date"] > "2026-08-31":
                continue
            k = keyfn(r)
            if k is None:
                continue
            agg[k][0] += r["resid"]
            agg[k][1] += 1
        return {k: (s / n) * (n / (n + SHRINK_K))
                for k, (s, n) in agg.items()}, \
               {k: n for k, (s, n) in agg.items()}

    frame_static, frame_n = build_table(
        lambda r: (r["box"], r["course"], r["frame"])
        if r["frame"] else None)
    style_static, style_n = build_table(
        lambda r: (r["box"], r["course"], r["tercile"])
        if r["tercile"] is not None else None)

    # ---- weekly components (trailing 28d, earlier races only) -----
    by_course_frame = defaultdict(list)
    by_course_style = defaultdict(list)
    for r in rows:
        if r["frame"]:
            by_course_frame[(r["box"], r["course"], r["frame"])].append(r)
        if r["tercile"] is not None:
            by_course_style[(r["box"], r["course"], r["tercile"])].append(r)
    for table in (by_course_frame, by_course_style):
        for k in table:
            table[k].sort(key=lambda r: r["date"])

    from datetime import date as _date, timedelta
    def weekly(table, key, tdate):
        items = table.get(key)
        if not items:
            return 0.0
        lo = (_date.fromisoformat(tdate) - timedelta(days=WEEKLY_DAYS)
              ).isoformat()
        sel = [r["resid"] for r in items if lo <= r["date"] < tdate]
        if not sel:
            return 0.0
        n = len(sel)
        return (sum(sel) / n) * (n / (n + SHRINK_K))

    # ---- features for record races + primary window ---------------
    target_races = {r["race_id"] for r in rows} | set(bases)
    features = {}
    for rid in sorted(target_races):
        meta = race_meta.get(rid)
        if meta is None:
            continue
        box = "jra" if rid.startswith("jra-") else "nar"
        course = (meta["track"], meta["surface"], meta["distance"])
        tdate = meta["date"]
        nums = set()
        for (rrid, n) in frames:
            if rrid == rid:
                nums.add(n)
        per = {}
        for n in sorted(nums):
            nk = natkey_of.get((rid, n))
            style = style_tendency(card_runs.get((rid, nk), []))
            ter = tercile(box, style)
            fr = frames.get((rid, n))
            per[n] = {
                "frame_static": frame_static.get((box, course, fr), 0.0)
                if fr else 0.0,
                "frame_weekly": weekly(by_course_frame,
                                       (box, course, fr), tdate)
                if fr else 0.0,
                "style_static": style_static.get((box, course, ter), 0.0)
                if ter is not None else 0.0,
                "style_weekly": weekly(by_course_style,
                                       (box, course, ter), tdate)
                if ter is not None else 0.0,
                "style": style, "tercile": ter, "frame": fr,
                "field": None, "surface": meta["surface"],
                "distance": meta["distance"],
            }
        features[rid] = per
    out = {"features": features,
           "frame_table_n": {str(k): v for k, v in frame_n.items()},
           "style_table_n": {str(k): v for k, v in style_n.items()},
           "terciles": {k: list(v) for k, v in terciles.items()},
           "residual_rows": len(rows)}
    (common.SCRATCH / "m3_features.pkl").write_bytes(pickle.dumps(out))
    summary = {"residual_rows": len(rows),
               "frame_cells": len(frame_static),
               "style_cells": len(style_static),
               "terciles": out["terciles"],
               "feature_races": len(features)}
    (common.SCRATCH / "m3_feature_stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
