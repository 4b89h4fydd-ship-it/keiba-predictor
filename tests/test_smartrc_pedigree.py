"""SmartRc's existing configured feed may hydrate lineage, not old scores."""
import copy
import inspect

import app
from arvexq.prediction.special_races import build_special_race_box


def _debut_card():
    return {"id": "jra-2026-10-25-東京-05", "circuit": "中央",
            "date": "2026-10-25", "title": "2歳新馬", "horses": [
                {"horseNumber": 2, "name": "テスト馬"},
                {"horseNumber": 3, "name": "別の馬"}]}


def test_smartrc_pedigree_names_decode_from_real_public_field_names():
    sample = {"uno": "2", "hname": "テスト馬",
              "f_name": "父名", "m_name": "母名", "mf_name": "母父名",
              "fmf_name": "父母父名", "mmf_name": "母母父名",
              "ten1f_best": 12.4}
    row = app._smart_normalize_row(sample)
    assert row["pedigree"] == {
        "sire": "父名", "dam": "母名", "damSire": "母父名",
        "sireDamSire": "父母父名", "damDamSire": "母母父名"}


def test_fetched_pedigree_merges_using_existing_path_without_changing_mark_or_bet():
    race = _debut_card()
    race["horses"][0]["integratedEvaluation"] = {"mark": "◎"}
    race["preRaceBet"] = {"items": [{"kind": "3連単", "combos": [[2, 3, 1]]}]}
    original = copy.deepcopy(race)
    row = app._smart_normalize_row({
        "uno": 2, "hname": "テスト馬", "f_name": "父名", "m_name": "母名",
        "mf_name": "母父名"})
    only_lineage = {"horseNumber": row["horseNumber"],
                    "name": row["name"], "pedigree": row["pedigree"]}
    result = app._merge_enrichment(race, {"smartRows": [only_lineage]})
    assert result["horses"][0]["pedigree"]["damSire"] == "母父名"
    assert "pedigree" not in result["horses"][1]
    assert result["horses"][0]["integratedEvaluation"] == original["horses"][0]["integratedEvaluation"]
    assert result["preRaceBet"] == original["preRaceBet"]
    specialist = build_special_race_box(result)
    assert "sire" in specialist["horses"][0]["observedFields"]
    assert "damSire" in specialist["horses"][0]["observedFields"]


def test_unpublished_or_empty_lineage_remains_missing():
    sample = {"uno": "2", "hname": "テスト馬", "f_name": "", "m_name": None, "mf_name": ""}
    row = app._smart_normalize_row(sample)
    assert "pedigree" not in row
    assert "sire" in build_special_race_box(_debut_card())["horses"][0]["missingFields"]


def test_existing_feed_contract_stays_optional_and_original_metrics_suspended():
    code = inspect.getsource(app._start_enrichment)
    assert 'os.getenv("SMARTRC_FEED_URL","").strip()' in code
    assert 'snap.get("circuit")!="中央"' in code
    assert '"pedigree":h["pedigree"]' in code
    assert 'return [{"horseNumber":h.get("horseNumber")' in code
