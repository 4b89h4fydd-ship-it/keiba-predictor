import copy
import pytest
from scripts.arvexq_data_foundation_audit import profile_bundle, analytics_rows
from arvexq.ingest.full_snapshot_codec import pack_detail
from arvexq.databanks.source_catalog import discovery_inventory


def bundle():
    d = {"id": "jra-2026-10-25-京都-05", "date": "2026-10-25", "circuit": "中央",
         "title": "2歳新馬", "fieldSize": 1, "horses": [{"horseNumber": 1,
         "pedigree": {"sire": "父", "dam": "母", "damsire": "母父"}}]}
    return {"date": d["date"], "races": [d], "details": [pack_detail(d)]}


def test_audit_decodes_full_envelopes_and_does_not_claim_preoff_evidence():
    b = bundle()
    original = copy.deepcopy(b)
    r = profile_bundle(b)
    s = r["segments"][0]
    assert s["pedigreeCompleteHorses"] == 1
    assert s["preoffEvidencePresentRaces"] == 0
    assert s["kind"] == "debut"
    assert s["missingRates"]["historyPresentHorses"] == 1
    assert len(list(analytics_rows(b))) == 1
    assert b == original


def test_invalid_envelope_missing_detail_and_duplicate_rows_block_import():
    for mode in ("digest", "missing", "duplicate", "date"):
        b = bundle()
        if mode == "digest": b["details"][0]["arvexqFullPayload"]["sha256"] = "bad"
        if mode == "missing": b["details"] = []
        if mode == "duplicate": b["details"] *= 2
        if mode == "date": b["date"] = "2026-10-24"
        with pytest.raises(ValueError): list(analytics_rows(b))


def test_catalog_does_not_equate_discovery_with_extraction_or_measured_success():
    rows = discovery_inventory()
    assert len(rows) >= 40
    assert len({r["id"] for r in rows}) == len(rows)
    assert all(r["enabledForExtraction"] is False for r in rows)
    assert all(r["measuredSuccessRate"] is None for r in rows)
    assert next(r for r in rows if r["id"] == "jbis")["policyStatus"] == "commercial-preparation-restricted"


def test_readback_matches_existing_venue_exclusion_without_deleting_raw_evidence():
    from scripts.arvexq_fetch_d1_bundle import supported_race
    b = bundle()
    excluded = {"id": "nar-2026-10-25-帯広ば-01", "track": "帯広ば"}
    b["races"].append(excluded)
    assert not supported_race(excluded)
    r = profile_bundle(b)
    assert r["expectedD1SummaryRaces"] == 1
    assert r["excludedRaceIds"] == [excluded["id"]]
    assert len(list(analytics_rows(b))) == 1
    assert len(b["races"]) == 2
