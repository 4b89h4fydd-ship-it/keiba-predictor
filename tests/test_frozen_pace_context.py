"""No lookahead in race-relative, frozen historical pace evidence."""
from copy import deepcopy
from datetime import date, timedelta, datetime, timezone
from math import isclose
import pytest

from arvexq.forecast.frozen_pace_context import build_preoff_pace_context, NAMES

EARLY="history::all::w5::early_speed"
LATE="history::all::w5::late_speed"
CORNER="history::all::w5::position_quality"


def race(day, *, outcome=1, evidence=True):
    jst=timezone(timedelta(hours=9))
    post=int(datetime.fromisoformat(day+"T12:00").replace(tzinfo=jst).timestamp())
    rows=[]
    for i in range(1,5):
        features={"history::all::w5::finish_quality::mean":(5-i)/5,
                  "static::age":3+i}
        if evidence:
            features.update({EARLY+"::mean":i*.5, EARLY+"::count":4.,
                             LATE+"::mean":(5-i)*.4, LATE+"::count":4.,
                             CORNER+"::mean":i*.2, CORNER+"::count":4.})
        rows.append({"horseNumber":i, "finish": 1 if i==outcome else
                     (i+1 if i<outcome else i), "features":features})
    return {"raceId":"中央-flat-"+day,"date":day,"circuit":"中央","family":"flat",
            "capturedAtEpoch":post-1800,"postAtEpoch":post,
            "snapshotHash":"sha256:0123456789abcdef0123456789abcdef",
            "declaredHorseNumbers":[1,2,3,4], "horses":rows}


def test_pace_proxy_from_past_only_and_order_invariant():
    case=race("2026-09-01")
    before=deepcopy(case)
    values=build_preoff_pace_context(case)
    assert case==before
    assert len(values)==4 and all(len(x)==len(NAMES) for x in values)
    assert all(all(-1<=v<=1 for v in x) for x in values)
    # Fastest historical early index has the highest observed relative rank.
    assert values[3][0]==1.0
    assert values[2][3]>0
    swapped=deepcopy(case)
    swapped["horses"]=list(reversed(swapped["horses"]))
    values_swapped=build_preoff_pace_context(swapped)
    assert values==list(reversed(values_swapped))


def test_no_pace_evidence_keeps_missingness_not_fabricated_speed():
    case=race("2026-09-02", evidence=False)
    values=build_preoff_pace_context(case)
    assert all(v[:5]==[0.,0.,0.,0.,0.] and v[5:]==[1.,1.,1.] for v in values)
    case["horses"][0]["features"][EARLY+"::mean"]=9
    case["horses"][0]["features"][EARLY+"::count"]=1
    assert build_preoff_pace_context(case)==values




def test_untrusted_or_absent_frozen_features_rejected():
    with pytest.raises(ValueError):
        build_preoff_pace_context({"horses":[{"features":{}}, {},{"features":{}}]})
    broken=race("2026-09-04")
    broken["horses"][0]["features"][EARLY+"::mean"]=float("nan")
    values=build_preoff_pace_context(broken)
    assert values[0][5]==1.
