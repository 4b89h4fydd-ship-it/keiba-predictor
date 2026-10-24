import ast
from pathlib import Path
import asyncio
from arvexq.databanks.smartrc import pedigree_rows, build_smartrc_source
from arvexq.databanks.registry import DataBankRegistry
from arvexq.ingest.fallback_enrichment import enrich_race_missing


def fixture_fetch(race):
    return {"status": "done", "rows": [{"horseNumber": 1, "name": "馬",
        "pedigree": {"sire": "父", "dam": "母", "damsire": "母父"},
        "smartRc": {"ten1f": 999}, "pedigreeScore": 999}]}


def test_no_unconfigured_network_and_no_rating_fields():
    def forbidden(*args): raise AssertionError("unconfigured feed called")
    assert pedigree_rows(forbidden, {}, configured=False) == []
    assert build_smartrc_source(forbidden, configured=False) is None
    rows = pedigree_rows(fixture_fetch, {}, configured=True)
    assert set(rows[0]) == {"horseNumber", "name", "pedigree"}


def test_same_number_wrong_name_and_ambiguous_rows_are_rejected():
    source = build_smartrc_source(fixture_fetch, configured=True)
    fetch = source.fetchers["pedigree"]
    assert fetch({"horseNumber": 1, "name": "別馬"}, {}) == {}
    assert fetch({"horseNumber": 2, "name": "馬"}, {}) == {}
    def duplicate(race):
        d = fixture_fetch(race); d["rows"] *= 2; return d
    assert build_smartrc_source(duplicate, configured=True).fetchers["pedigree"]({"horseNumber": 1, "name": "馬"}, {}) == {}


def test_both_circuits_reuse_existing_fallback_for_partial_pedigree():
    reg = DataBankRegistry()
    reg.register(build_smartrc_source(fixture_fetch, configured=True))
    for circuit in ("中央", "地方"):
        race = {"circuit": circuit, "date": "2026-10-25", "horses": [
            {"horseNumber": 1, "name": "馬", "pedigree": {"sire": "公式父"}}]}
        out = asyncio.run(enrich_race_missing(race, bank_registry=reg))
        assert out["horses"][0]["pedigree"] == {"sire": "公式父", "dam": "母", "damsire": "母父"}
        assert "smartRc" not in out["horses"][0]


def test_existing_feed_normalizer_keeps_observed_ancestry():
    from arvexq.ingest.pure_parsers import _pick
    from arvexq.ingest.environment_values import _safe_int
    tree = ast.parse(Path("app.py").read_text())
    f = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_smart_normalize_row")
    ns = {"_pick": _pick, "_safe_int": _safe_int}
    exec(compile(ast.Module(body=[f], type_ignores=[]), "app.py", "exec"), ns)
    assert ns[f.name]({"馬番": 1, "馬名": "馬", "父": "父", "母": "母", "母父": "母父"})["pedigree"] == {"sire": "父", "dam": "母", "damsire": "母父"}
