"""Complete existing D1-overlay-to-seal fusion smoke with trained 5 methods.

Synthetic race results verify control flow only; accuracy is separately
measured on real official, strictly later holdout races.
"""
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_fusion_historical_replay import sixty, card
from arvexq.prediction.fusion_historical_replay import train_and_validate
from arvexq.prediction.fusion_source_composer import assemble_fusion_inputs
from arvexq.forecast.engine import build_prediction,VERSION
from arvexq.forecast.publication import public_race
from scripts.arvexq_apply_learned_overlay import apply
from scripts.arvexq_freeze_predictions import prepare_seal, capture_original_bet

NOW=datetime(2026,10,24,10,0,tzinfo=ZoneInfo("Asia/Tokyo"))


def target():
    d=card("2026-10-24")
    d.pop("result")
    d["officialPreoffTicketOdds"]={
        "sourceKind":"official_preoff_quotes",
        "capturedAt":"2026-10-24T09:00:00+09:00",
        "prices":[
            {"kind":"3連単","combo":[1,2,3],"odds":500.},
            {"kind":"3連複","combo":[1,2,3],"odds":50.},
            {"kind":"馬連","combo":[1,2],"odds":25.},
            {"kind":"ワイド","combo":[1,2],"odds":10.},
        ],
    }
    return d


def test_five_arms_real_product_marks_tickets_and_original_seal():
    fitted=train_and_validate(sixty(),circuit="地方",target_date="2026-10-24")
    d=target()
    original=deepcopy(d)
    receipt=assemble_fusion_inputs(
        d,fitted["models"],fitted["calibration"],now=NOW)
    assert len(receipt["opinions"])==5
    assert receipt["calibration"]["nRaces"]>=30
    assert receipt["capturedAt"]<receipt["scheduledOffAt"]
    prepared=dict(d,fusionInputs={
        "opinions":receipt["opinions"],
        "calibration":receipt["calibration"],
        "odds":receipt["odds"],
        "capturedAt":receipt["capturedAt"],
    })
    response=build_prediction(prepared,now=NOW)
    assert response is not None
    assert response["modelVersion"]==VERSION
    assert response["humanOverrideAllowed"] is False
    assert len(response["predictionMarks"])==5
    assert sum(x["points"] for x in response["recommendedBets"])<=5
    with patch("scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction",return_value=True):
        output,report=apply({"details":[d]},
            {"fusion":{"地方":fitted}},now=NOW)
    assert report["fusionPublished"]==[d["id"]],report
    assert not report["fusionErrors"]
    saved=output["details"][0]
    assert "fusionInputs" not in saved
    assert saved["predictionModelVersion"]==VERSION
    assert len(saved["predictionMarks"])==5
    assert len(saved["fusionMethodPreoffReceipt"]["arms"])==5
    locked=prepare_seal(saved,now=NOW)
    assert locked["status"]=="sealed",locked
    assert locked["detail"]["preRacePrediction"]["markCount"]==5
    assert locked["detail"]["preRaceMethodOriginal"]["sourceKind"]=="original-frozen-preoff-method-opinions"
    bet=capture_original_bet(locked["detail"],NOW)
    assert bet["decision"] in ("推奨","見送り")
    assert d==original


def test_projection_of_stored_fusion_original_never_forges_postoff_pick():
    fitted=train_and_validate(sixty(),circuit="地方",target_date="2026-10-24")
    with patch("scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction",return_value=True):
        bundle,_=apply({"details":[target()]},{"fusion":{"地方":fitted}},now=NOW)
    saved=bundle["details"][0]
    published=public_race({**saved,"result":{"status":"確定","finishers":[
        {"horseNumber":1,"finish":1}]}})
    assert published["predictionMarks"]==saved["predictionMarks"]
    assert published["recommendedBets"]==saved["recommendedBets"]
    assert published["predictionModelVersion"]==VERSION
    assert "fusionInputs" not in published
