"""Research-only replay over existing static snapshots and independently retrieved labels.

The current snapshots were archived after race dates: NOT a forward-validated
preoff prediction record. Labels are used strictly after all predictions, and
no outcome keys are ever passed to Stage64. Never use this as product accuracy.
"""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import warnings

from arvexq.research.stage64.pipeline import predict

ROOT = Path(__file__).resolve().parents[1]
LABELS = json.loads(r'''{"jra-2026-10-17-京都-01":[2,9,3],"jra-2026-10-17-京都-02":[7,6,1],"jra-2026-10-17-京都-03":[4,5,8],"jra-2026-10-17-京都-04":[5,2,1],"jra-2026-10-17-京都-05":[1,2,4],"jra-2026-10-17-京都-06":[4,10,8],"jra-2026-10-17-京都-07":[7,4,8],"jra-2026-10-17-京都-08":[7,3,6],"jra-2026-10-17-京都-09":[7,11,14],"jra-2026-10-17-京都-10":[6,2,7],"jra-2026-10-17-京都-11":[10,5,9],"jra-2026-10-17-京都-12":[5,7,10],"jra-2026-10-17-新潟-01":[9,2,7],"jra-2026-10-17-新潟-02":[7,11,1],"jra-2026-10-17-新潟-03":[2,5,1],"jra-2026-10-17-新潟-04":[7,11,10],"jra-2026-10-17-新潟-05":[11,3,15],"jra-2026-10-17-新潟-06":[11,15,2],"jra-2026-10-17-新潟-07":[6,4,7],"jra-2026-10-17-新潟-08":[2,4,13],"jra-2026-10-17-新潟-09":[3,9,1],"jra-2026-10-17-新潟-10":[10,6,3],"jra-2026-10-17-新潟-11":[6,12,15],"jra-2026-10-17-新潟-12":[16,14,8],"jra-2026-10-17-東京-01":[4,2,6],"jra-2026-10-17-東京-02":[4,9,8],"jra-2026-10-17-東京-03":[11,8,6],"jra-2026-10-17-東京-04":[5,17,15],"jra-2026-10-17-東京-05":[9,7,3],"jra-2026-10-17-東京-06":[13,17,7],"jra-2026-10-17-東京-07":[5,11,4],"jra-2026-10-17-東京-08":[6,4,3],"jra-2026-10-17-東京-09":[7,12,5],"jra-2026-10-17-東京-10":[4,10,14],"jra-2026-10-17-東京-11":[13,10,14],"jra-2026-10-17-東京-12":[2,7,5],"nar-2026-10-15-名古屋-01":[1,10,7],"nar-2026-10-15-名古屋-02":[11,4,2],"nar-2026-10-15-名古屋-03":[6,2,1],"nar-2026-10-15-名古屋-04":[9,6,3],"nar-2026-10-15-名古屋-05":[7,6,1],"nar-2026-10-15-名古屋-06":[2,1,3],"nar-2026-10-15-名古屋-07":[6,4,5],"nar-2026-10-15-名古屋-08":[6,8,9],"nar-2026-10-15-名古屋-09":[7,2,1],"nar-2026-10-15-名古屋-10":[6,3,4],"nar-2026-10-15-名古屋-11":[5,4,12],"nar-2026-10-15-名古屋-12":[6,7,11],"nar-2026-10-15-園田-01":[6,10,1],"nar-2026-10-15-園田-02":[8,7,3],"nar-2026-10-15-園田-03":[5,1,4],"nar-2026-10-15-園田-04":[4,2,8],"nar-2026-10-15-園田-05":[12,8,4],"nar-2026-10-15-園田-06":[4,5,9],"nar-2026-10-15-園田-07":[5,2,8],"nar-2026-10-15-園田-08":[4,9,5],"nar-2026-10-15-園田-09":[2,3,6],"nar-2026-10-15-園田-10":[9,3,8],"nar-2026-10-15-園田-11":[2,4,6],"nar-2026-10-15-園田-12":[7,3,6],"nar-2026-10-15-川崎-01":[7,8,3],"nar-2026-10-15-川崎-02":[6,2,8],"nar-2026-10-15-川崎-03":[9,8,7],"nar-2026-10-15-川崎-04":[4,6,2],"nar-2026-10-15-川崎-05":[11,10,7],"nar-2026-10-15-川崎-06":[7,13,1],"nar-2026-10-15-川崎-07":[7,2,3],"nar-2026-10-15-川崎-08":[8,2,1],"nar-2026-10-15-川崎-09":[3,12,2],"nar-2026-10-15-川崎-10":[5,10,6],"nar-2026-10-15-川崎-11":[2,7,6],"nar-2026-10-15-川崎-12":[14,1,9],"nar-2026-10-15-門別-01":[8,3,5],"nar-2026-10-15-門別-02":[6,4,7],"nar-2026-10-15-門別-03":[11,3,7],"nar-2026-10-15-門別-04":[8,1,3],"nar-2026-10-15-門別-05":[1,4,3],"nar-2026-10-15-門別-06":[4,7,5],"nar-2026-10-15-門別-07":[10,2,7],"nar-2026-10-15-門別-08":[4,7,2],"nar-2026-10-15-門別-09":[4,10,8],"nar-2026-10-15-門別-10":[9,2,1],"nar-2026-10-15-門別-11":[5,7,3],"nar-2026-10-15-門別-12":[7,9,8],"nar-2026-10-17-佐賀-01":[5,4,6],"nar-2026-10-17-佐賀-02":[1,8,6],"nar-2026-10-17-佐賀-03":[7,2,1],"nar-2026-10-17-佐賀-04":[6,4,7],"nar-2026-10-17-佐賀-05":[13,5,12],"nar-2026-10-17-佐賀-06":[1,5,7],"nar-2026-10-17-佐賀-07":[8,1,3],"nar-2026-10-17-佐賀-08":[1,6,8],"nar-2026-10-17-佐賀-09":[2,3,7],"nar-2026-10-17-佐賀-10":[8,7,6],"nar-2026-10-17-佐賀-11":[7,8,5],"nar-2026-10-17-帯広ば-01":[3,7,6],"nar-2026-10-17-帯広ば-02":[2,4,9],"nar-2026-10-17-帯広ば-03":[5,9,7],"nar-2026-10-17-帯広ば-04":[1,7,6],"nar-2026-10-17-帯広ば-05":[4,10,5],"nar-2026-10-17-帯広ば-06":[2,1,6],"nar-2026-10-17-帯広ば-07":[1,4,3],"nar-2026-10-17-帯広ば-08":[4,2,6],"nar-2026-10-17-帯広ば-09":[9,4,6],"nar-2026-10-17-帯広ば-10":[5,8,7],"nar-2026-10-17-帯広ば-11":[6,7,9],"nar-2026-10-17-帯広ば-12":[4,5,8],"nar-2026-10-17-高知-01":[1,6,3],"nar-2026-10-17-高知-02":[5,11,12],"nar-2026-10-17-高知-03":[8,7,10],"nar-2026-10-17-高知-04":[9,8,2],"nar-2026-10-17-高知-05":[8,7,10],"nar-2026-10-17-高知-06":[9,6,2],"nar-2026-10-17-高知-07":[10,7,1],"nar-2026-10-17-高知-08":[7,4,5],"nar-2026-10-17-高知-09":[9,11,4],"nar-2026-10-17-高知-10":[7,5,8],"nar-2026-10-17-高知-11":[9,7,5]}''')


def _existing_snapshot(race_id):
    date = "-".join(race_id.split("-")[1:4])
    root = ROOT / "arvexq/ui/static/saved-snapshots"
    catalog = json.loads((root / (date + ".json")).read_text(encoding="utf-8"))
    meta = catalog["races"].get(race_id)
    if meta is None:
        return None
    packed = json.loads((root / meta["file"]).read_text(encoding="utf-8"))
    raw = gzip.decompress(base64.b64decode(packed["gzipBase64"]))
    assert len(raw) == packed["bytes"]
    assert hashlib.sha256(raw).hexdigest() == packed["sha256"]
    full = json.loads(raw)
    if full.get("id") != race_id or full.get("date") != date:
        raise AssertionError("archive identity mismatch")
    # Explicit allow-list prevents result, payouts, race-day diagnosis and odds
    # from entering the prediction candidate.
    owner = full.get("circuit")
    owner = {"中央": "jra", "地方": "nar"}.get(owner, owner)
    horses = []
    for horse in full.get("horses") or []:
        source = horse.get("recentRaces") or (
            horse.get("allPastRuns") if owner == "nar" else None) or []
        # Full career is accessible for same-track facts only; Stage64 never
        # uses future/outcome runs because all runs are date-fenced.
        horses.append({
            "horseNumber": horse.get("horseNumber"),
            "frameNumber": horse.get("frameNumber"),
            "status": horse.get("status"),
            "scratched": horse.get("scratched"),
            "recentRaces": source,
            "allPastRuns": horse.get("allPastRuns") or [],
        })
    return {
        "id": race_id, "date": date, "circuit": owner,
        "analysisMode": full.get("analysisMode"),
        "track": full.get("track"), "surface": full.get("surface"),
        "distance": full.get("distance"),
        "fieldSize": full.get("fieldSize"), "horses": horses,
    }


def test_two_date_replay_baselines_and_public_tactics():
    judged = []
    for race_id in sorted(LABELS):
        if "帯広ば" in race_id:
            continue
        source = _existing_snapshot(race_id)
        if source is None:
            continue
        if source.get("analysisMode") == "障害" or source.get("surface") == "障害":
            continue
        try:
            plain = predict(source, expected_circuit=source["circuit"])
            recent = predict(source, expected_circuit=source["circuit"],
                             ability_method="recent5")
        except (ValueError, KeyError, TypeError):
            continue
        stages = plain["stages"]
        if any(stages[key]["value"] is None for key in ("marks", "pace")):
            continue
        win_order = stages["marks"]["value"]["orderedWinCandidates"]
        recent_order = recent["stages"]["marks"]["value"]["orderedWinCandidates"]
        tactics = plain["paceEvidence"]["publicPositionTactics"]
        course = plain["paceEvidence"]["historicalCourseEvidence"]
        # Two qualitative candidates for comparison ONLY; not used by product.
        # No weighted score and no retrospective label-dependent changes.
        course_winners = [h for h in win_order[:5] if
            (course.get(h) or {}).get("sameTrackDistanceWins", 0) > 0]
        explicit_course = course_winners[0] if course_winners else win_order[0]
        segregated = set(tactics["separatedForwardIntentCandidates"])
        distinct_front = next((h for h in win_order[:3] if h in segregated),
                              win_order[0])
        # Freeze all four candidate predictions before opening labels.
        challenger = (plain.get("winnerEvidenceComparison") or {}).get(
            "proposedHeadToHeadResearchChallenger")
        rematch = challenger["horseNumber"] if challenger else win_order[0]
        judged.append((race_id, source["circuit"], win_order[0],
                       recent_order[0], explicit_course, distinct_front,
                       rematch, bool(challenger)))
    assert len(judged) >= 30, "insufficient comparable saved race history"
    report = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    rematch_triggers = defaultdict(int)
    for race_id, circuit, baseline, recent, course, separated, rematch, triggered in judged:
        winner, runnerup, third = LABELS[race_id]
        if triggered:
            rematch_triggers[("-".join(race_id.split("-")[1:4]), circuit)] += 1
        for method, n in (("baseline", baseline), ("recent5", recent),
                          ("explicitCourse", course),
                          ("isolatedForward", separated),
                          ("directRivalReplayOnly", rematch)):
            row = report[("-".join(race_id.split("-")[1:4]), circuit)][method]
            row[0] += 1
            row[1] += n == winner
            row[2] += n in (winner, runnerup, third)
    for (date, circuit), methods in sorted(report.items()):
        info = "; ".join("%s %d/%d◎1着 %d/%d◎3内" % (
            method, result[1], result[0], result[2], result[0])
            for method, result in sorted(methods.items()))
        info += "; directRivalTriggers=%d" % rematch_triggers[(date,circuit)]
        warnings.warn("ARVEXQ_RESEARCH_NOT_PREOFF %s %s: %s" %
                      (date, circuit, info), UserWarning, stacklevel=1)
