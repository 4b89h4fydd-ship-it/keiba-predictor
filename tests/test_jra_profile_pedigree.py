"""Original-source JRA pedigree integration; never invent pedigree or a bet."""
from __future__ import annotations

import asyncio
import copy

from arvexq.databanks.jra import build_jra_source
from arvexq.databanks.legacy_bridge import _jra_pedigree_adapter
from arvexq.databanks.registry import DataBankRegistry
from arvexq.ingest.fallback_enrichment import _needs_pedigree, enrich_race_missing
from arvexq.ingest.jra_profile_pedigree import parse_jra_profile_pedigree


PROFILE = """
<html><h2>競走馬情報</h2><section><h3>プロフィール</h3>
<table><tr><th>父</th><td>ディーマジェスティ</td></tr>
<tr><th>母</th><td>アマノブラウニイー産駒</td></tr>
<tr><th>母の父</th><td>サクラバクシンオー</td></tr></table></section>
</html>
"""


def test_official_profile_pedigree_parses_observed_lineage():
    assert parse_jra_profile_pedigree(PROFILE) == {
        "pedigree": {"sire": "ディーマジェスティ",
                     "dam": "アマノブラウニイー", "damSire": "サクラバクシンオー"}}


def test_alternative_definition_list_and_empty_page():
    html = "<dl><dt>父</dt><dd>父馬</dd><dt>母</dt><dd>母馬</dd><dt>母の父</dt><dd>母父</dd></dl>"
    assert parse_jra_profile_pedigree(html)["pedigree"] == {
        "sire": "父馬", "dam": "母馬", "damSire": "母父"}
    assert parse_jra_profile_pedigree("") == {}
    assert parse_jra_profile_pedigree("<p>競走馬情報なし</p>") == {}


def test_reuses_existing_jra_profile_endpoint_and_never_fabricates_missing_identity():
    called = []
    def existing_get(url, cname, cache_sec):
        called.append((url, cname, cache_sec))
        return PROFILE
    getter = _jra_pedigree_adapter({"_jra_request": existing_get})
    race = {"date": "2026-10-25", "circuit": "中央"}
    assert getter({"_jraHorseCname": "pw01dud002024105058/81"}, race)["pedigree"]["damSire"] == "サクラバクシンオー"
    assert called == [("https://www.jra.go.jp/JRADB/accessU.html",
                       "pw01dud002024105058/81", 86400)]
    assert getter({"name": "horse-without-profile-identity"}, race) == {}
    assert getter({"_jraHorseCname": "pw01dud002024105058/81"}, {"date": "2026-10-25", "circuit": "地方"}) == {}
    assert len(called) == 1


def test_missing_dam_and_damsire_triggers_existing_pedigree_provider():
    assert _needs_pedigree({"pedigree": {"sire": "先に取得した父"}})
    assert not _needs_pedigree({"pedigree": {
        "sire": "父", "dam": "母", "damSire": "母父"}})


def test_registered_existing_source_fills_gaps_but_not_marks_or_earlier_parent():
    def existing_get(url, cname, cache_sec):
        return PROFILE
    source = build_jra_source(pedigree=_jra_pedigree_adapter({"_jra_request": existing_get}))
    registry = DataBankRegistry()
    registry.register(source)
    assert [s.name for s in registry.providers("pedigree", circuit="JRA")] == ["jra_official"]
    assert registry.providers("pedigree", circuit="NAR") == []
    detail = {
        "id": "jra-2026-10-25-東京-05", "date": "2026-10-25",
        "circuit": "中央", "title": "2歳新馬",
        "horses": [{"horseNumber": 1, "name": "試験馬",
                    "_jraHorseCname": "pw01dud002024105058/81",
                    "pedigree": {"sire": "既存の父"},
                    "integratedEvaluation": {"mark": "◎"}}],
        "preRaceBet": {"items": [{"kind": "3連単", "combos": [[1, 2, 3]]}]},
    }
    original = copy.deepcopy(detail)
    enriched = asyncio.run(enrich_race_missing(detail, bank_registry=registry, history_limit=5))
    p = enriched["horses"][0]["pedigree"]
    assert p["sire"] == "既存の父"  # never overwrite competing factual evidence
    assert p["dam"] == "アマノブラウニイー"
    assert p["damSire"] == "サクラバクシンオー"
    assert "jra_official" in enriched["horses"][0]["_supplementalSources"]
    assert enriched["preRaceBet"] == original["preRaceBet"]
    assert enriched["horses"][0]["integratedEvaluation"] == original["horses"][0]["integratedEvaluation"]
    assert detail == original


def test_no_guessing_from_result_labels():
    html = "<table><tr><th>着順</th><td>1</td></tr><tr><th>馬名</th><td>勝者</td></tr></table>"
    assert parse_jra_profile_pedigree(html) == {}
