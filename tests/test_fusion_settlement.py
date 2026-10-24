"""Official-finish settlement tests. Fixtures are synthetic, not performance claims."""
from copy import deepcopy
from datetime import date, timedelta

import pytest

from arvexq.prediction.fusion_settlement import (
    VERSION, settle_frozen_race, train_from_frozen_results,
)

NAMES = ("mineta", "expert:form", "expert:course", "ai:learned", "ai:mass")


def evidence(day="2026-10-20"):
    rid = "nar-" + day + "-園田-01"
    horses = [{"horseNumber": n, "name": "馬" + str(n)} for n in range(1, 6)]
    official = {
        "id": rid, "date": day, "circuit": "地方", "horses": horses,
        "result": {
            "status": "確定", "source": "NAR-official",
            "finishers": [{"horseNumber": n, "finish": n} for n in range(1, 6)],
            "payouts": [{"type": "単勝", "combination": "1", "amount": 420},
                        {"type": "3連単", "combination": "1-2-3", "amount": 7000}],
        },
    }
    opinions = {}
    for name in NAMES:
        leader = 1 if name in ("mineta", "ai:learned") else 2
        win = {n: (0.6 if n == leader else 0.1) for n in range(1, 6)}
        opinions[name] = {
            "modelVersion": name + "/v1", "evidenceId": rid + "/" + name,
            "raceId": rid, "capturedAt": day + "T09:00:00+09:00",
            "win": win, "top3": {n: 0.6 for n in range(1, 6)},
        }
    receipt = {
        "raceId": rid, "raceDate": day, "circuit": "地方",
        "capturedAt": day + "T09:05:00+09:00",
        "scheduledOffAt": day + "T12:00:00+09:00",
        "sourceKind": "original-frozen-preoff-method-opinions",
        "sourceVersions": {k: v["modelVersion"] for k, v in opinions.items()},
        "roster": [1, 2, 3, 4, 5], "arms": opinions,
    }
    return official, receipt


def test_one_race_real_ledger_derives_stakes_and_returns_from_verified_payout_only():
    official, receipt = evidence()
    original = deepcopy(receipt)
    row = settle_frozen_race(official, receipt)
    assert receipt == original
    assert row["settlementVersion"] == VERSION
    assert row["officialWinPayoutPer100Yen"] == 420
    assert row["arms"]["mineta"]["returnYen"] == 420
    assert row["arms"]["expert:course"]["returnYen"] == 0
    assert all(a["stakeYen"] == 100 for a in row["arms"].values())
    assert all("result" not in a for a in row["arms"].values())


def test_missing_actual_preoff_capture_and_bad_payout_are_never_reconstructed():
    official, receipt = evidence()
    receipt["capturedAt"] = "2026-10-20T12:01:00+09:00"
    with pytest.raises(ValueError, match="pre-off capture"):
        settle_frozen_race(official, receipt)
    official, receipt = evidence()
    receipt["sourceKind"] = "retrospective-derived-after-result"
    with pytest.raises(ValueError, match="sealed source"):
        settle_frozen_race(official, receipt)
    official, receipt = evidence()
    official["result"]["payouts"][0]["combination"] = "3"
    with pytest.raises(ValueError, match="conflicts"):
        settle_frozen_race(official, receipt)
    official, receipt = evidence()
    official["result"]["status"] = "速報"
    with pytest.raises(ValueError, match="final"):
        settle_frozen_race(official, receipt)


def test_thirty_original_races_fit_real_win_hit_and_payout_based_weighting():
    originals = [evidence((date(2026, 9, 1)+timedelta(days=i)).isoformat())
                 for i in range(30)]
    snapshots = [row for row, _ in originals]
    frozen = {receipt["raceId"]: receipt for _, receipt in originals}
    result = train_from_frozen_results(
        snapshots, frozen, circuit="地方", target_date="2026-10-24")
    fitted = result["calibration"]
    assert result["matchedRaces"] == 30
    assert fitted["nRaces"] == 30
    assert fitted["weights"]["mineta"] == pytest.approx(0.5)
    assert fitted["weights"]["ai:learned"] == pytest.approx(0.5)
    assert fitted["metrics"]["mineta"]["roi"] == pytest.approx(4.2)
    assert fitted["metrics"]["expert:form"]["roi"] == 0


def test_no_preoff_archives_fails_closed_instead_of_faking_replay():
    snapshots = [evidence((date(2026, 9, 1)+timedelta(days=i)).isoformat())[0]
                 for i in range(30)]
    with pytest.raises(ValueError, match="insufficient"):
        train_from_frozen_results(snapshots, {}, circuit="地方",
                                  target_date="2026-10-24")
    with pytest.raises(ValueError, match="explicit circuit"):
        train_from_frozen_results(snapshots, {}, circuit="central/local",
                                  target_date="2026-10-24")
