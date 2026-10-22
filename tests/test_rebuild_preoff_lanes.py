"""Six-lane research gate: real frozen inputs, separate JRA/NAR, never picks."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from arvexq.rebuild.preoff_lanes import inspect_jra, inspect_nar, inspect_preoff, LANES


JST = timezone(timedelta(hours=9))
DAY = "2026-10-22"


def hashed(value):
    return sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str,
    ).encode("utf-8")).hexdigest()


def sample(circuit="中央", track="東京", family="flat"):
    rid = ("jra-" if circuit == "中央" else "nar-") + DAY + "-" + track + "-03"
    features = [
        {"history::all::w5::finish_quality::mean": .65,
         "history::all::w5::early_speed::mean": .55,
         "history::all::w5::late_speed::mean": .40,
         "market::win_odds": 3.2},
        {"history::all::w5::finish_quality::mean": .4,
         "history::all::w5::position_quality::mean": .52},
        {},
    ]
    snapshot = {
        "snapshotVersion": "arvexq-mass-feature-snapshot-v2",
        "schemaVersion": "arvexq-mass-features-v2-temporal-and-speed-separation",
        "raceId": rid, "date": DAY, "circuit": circuit, "track": track,
        "surface": "障害" if family == "jumps" else "ダート",
        "horseCount": 3,
        "rows": [{"horseNumber": n, "name": f"runner-{n}", "features": features[n - 1]}
                 for n in (1, 2, 3)],
    }
    snapshot["featureHash"] = hashed(snapshot)
    receipt = {
        "version": "arvexq-preoff-raw-evidence-v1",
        "source": "preoff-acquisition-log",
        "attestedPreOff": True,
        "raceId": rid,
        "featureHash": snapshot["featureHash"],
        "activeHorseNumbers": [1, 2, 3],
        "capturedAtEpoch": int(datetime(2026, 10, 22, 9, 0, tzinfo=JST).timestamp()),
        "postAtEpoch": int(datetime(2026, 10, 22, 15, 0, tzinfo=JST).timestamp()),
    }
    receipt["receiptHash"] = hashed(receipt)
    return snapshot, receipt


def resign(snapshot, receipt):
    snapshot["featureHash"] = hashed({k: v for k, v in snapshot.items() if k != "featureHash"})
    receipt["featureHash"] = snapshot["featureHash"]
    receipt["receiptHash"] = hashed({k: v for k, v in receipt.items() if k != "receiptHash"})


def test_both_circuits_separate_and_six_lanes_never_publish_picks():
    for circuit, track, family in (("中央", "東京", "jra-flat"),
                                   ("地方", "大井", "nar-flat")):
        snapshot, receipt = sample(circuit, track)
        original = deepcopy((snapshot, receipt))
        report = inspect_preoff(snapshot, receipt)
        assert report["modelFamily"] == family
        assert list(report["lanes"]) == list(LANES)
        assert report["status"] == "research_only_not_publishable"
        assert report["independentStorageTimestampVerified"] is False
        assert report["horseNumbers"] == [1, 2, 3]
        assert report["lanes"]["ability"]["horsesWithEvidence"] == 2
        assert report["lanes"]["ability"]["status"] == "partial_evidence"
        assert report["lanes"]["running_style"]["horsesWithEvidence"] == 2
        assert report["lanes"]["pace_scenarios"]["predictedScenarios"] == []
        assert report["lanes"]["probabilities"]["win"] is None
        assert report["lanes"]["probabilities"]["top2"] is None
        assert report["lanes"]["probabilities"]["top3"] is None
        assert report["lanes"]["marks"]["items"] == []
        assert report["lanes"]["tickets"]["items"] == []
        assert (snapshot, receipt) == original


def test_direct_cross_circuit_invocation_rejected():
    s, r = sample("中央", "東京")
    with pytest.raises(ValueError, match="circuit mismatch"):
        inspect_nar(s, r)
    s, r = sample("地方", "大井")
    with pytest.raises(ValueError, match="circuit mismatch"):
        inspect_jra(s, r)


def test_result_fields_never_enter_research_gate():
    for target in ("snapshot", "row"):
        s, r = sample()
        if target == "snapshot":
            s["result"] = {"finishers": [1]}
        else:
            s["rows"][0]["labelWin"] = 1
        resign(s, r)
        with pytest.raises(ValueError, match="outcome-dependent|result-derived"):
            inspect_preoff(s, r)


def test_tampered_snapshot_origin_hash_rejected():
    s, r = sample()
    s["rows"][0]["features"]["history::all::w5::finish_quality::mean"] = 1.0
    with pytest.raises(ValueError, match="hash mismatch"):
        inspect_preoff(s, r)


def test_tampered_receipt_rejected_without_authentic_timestamp_proof():
    s, r = sample()
    r["capturedAtEpoch"] -= 60
    with pytest.raises(ValueError, match="receipt hash"):
        inspect_preoff(s, r)


def test_retroactively_claimed_capture_at_or_after_post_is_rejected():
    s, r = sample()
    r["capturedAtEpoch"] = r["postAtEpoch"]
    resign(s, r)
    with pytest.raises(ValueError, match="pre-off timestamp"):
        inspect_preoff(s, r)


def test_duplicate_missing_or_extra_horse_rejected():
    for change in ("duplicate", "extra", "absent"):
        s, r = sample()
        if change == "duplicate":
            s["rows"][1]["horseNumber"] = 1
        elif change == "extra":
            s["rows"].append({"horseNumber": 4, "name": "extra", "features": {}})
            s["horseCount"] = 4
        else:
            r["activeHorseNumbers"] = [1, 2]
        resign(s, r)
        with pytest.raises(ValueError, match="field|runner"):
            inspect_preoff(s, r)


def test_wrong_race_id_prefix_and_date_rejected():
    s, r = sample()
    s["raceId"] = s["raceId"].replace("jra-", "nar-")
    r["raceId"] = s["raceId"]
    resign(s, r)
    with pytest.raises(ValueError, match="identity and circuit"):
        inspect_preoff(s, r)


def test_obihiro_and_jumps_are_not_automatically_relabelled_flat():
    s, r = sample("地方", "帯広")
    with pytest.raises(ValueError, match="Banei"):
        inspect_preoff(s, r)
    s, r = sample("中央", "東京", "jumps")
    with pytest.raises(ValueError, match="Banei/jumps"):
        inspect_preoff(s, r)


def test_unknown_circuit_fails_without_fallback():
    s, r = sample()
    s["circuit"] = "混合"
    resign(s, r)
    with pytest.raises(ValueError, match="unsupported racing circuit"):
        inspect_preoff(s, r)


def test_nonsensical_preoff_receipt_or_missing_runner_name_rejected():
    s, r = sample()
    r.pop("receiptHash")
    with pytest.raises(ValueError, match="receipt hash"):
        inspect_preoff(s, r)
    s, r = sample()
    s["rows"][1]["name"] = ""
    resign(s, r)
    with pytest.raises(ValueError, match="name"):
        inspect_preoff(s, r)


def test_leaky_market_is_never_treated_as_ability_or_probability():
    s, r = sample()
    for row in s["rows"]:
        row["features"] = {"market::implied_raw": 0.8}
    resign(s, r)
    result = inspect_preoff(s, r)
    assert result["lanes"]["ability"]["horsesWithEvidence"] == 0
    assert result["lanes"]["running_style"]["horsesWithEvidence"] == 0
    assert result["lanes"]["probabilities"]["win"] is None


def test_receipt_checks_finite_and_valid_numeric_history_features():
    s, r = sample()
    s["rows"][0]["features"]["history::all::w5::finish_quality::mean"] = float("nan")
    # Historical data poisoning fails even when the recipient recomputes a hash.
    # JSON NaN is deliberately not a valid immutable feature proof.
    with pytest.raises((ValueError, TypeError)):
        inspect_preoff(s, r)
