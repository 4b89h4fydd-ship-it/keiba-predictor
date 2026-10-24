import asyncio
import copy

from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.fallback_enrichment import _merge_runs, enrich_race_missing
from arvexq.ingest.pedigree_merge import fill_pedigree, needs_pedigree


def test_partial_ancestry_is_missing_until_all_three_fields_are_present():
    assert needs_pedigree({"pedigree": {"sire": "父"}})
    assert needs_pedigree({"sire": "父", "dam": "母"})
    assert not needs_pedigree({"sire": "父", "pedigree": {"dam": "母", "damsire": "母父"}})


def test_partial_merge_preserves_canonical_facts_and_records_conflicts():
    horse = {"sire": "公式父", "pedigree": {"dam": "公式母"}}
    payload = {"pedigree": {"sire": "別父", "dam": "別母", "damsire": "母父"}}
    original = copy.deepcopy(payload)
    assert fill_pedigree(horse, payload, source="licensed_feed")
    assert horse["sire"] == "公式父"
    assert horse["pedigree"] == {"dam": "公式母", "damsire": "母父"}
    assert len([r for r in horse["_pedigreeEvidence"] if r["status"] == "conflict"]) == 2
    assert payload == original
    before = copy.deepcopy(horse)
    assert not fill_pedigree(horse, payload, source="licensed_feed")
    assert horse == before


def test_registered_pedigree_provider_is_called_for_partial_horse():
    reg = DataBankRegistry()
    calls = []
    def fetch(horse, race, limit):
        calls.append(horse["horseNumber"])
        return {"pedigree": {"sire": "別父", "dam": "母", "damsire": "母父"}}
    reg.register(DataSource("licensed_test", "JRA", 20, SourceCapabilities(pedigree=True),
                            {"pedigree": fetch}))
    race = {"circuit": "中央", "date": "2026-10-25", "horses": [
        {"horseNumber": 1, "pedigree": {"sire": "父"}}]}
    original = copy.deepcopy(race)
    out = asyncio.run(enrich_race_missing(race, bank_registry=reg))
    assert calls == [1]
    assert out["horses"][0]["pedigree"] == {"sire": "父", "dam": "母", "damsire": "母父"}
    assert race == original
    assert out["preparedMeta"]["supplementalSearch"]["changedHorses"] == 1
    audit = out["preparedMeta"]["supplementalSearch"]
    assert audit["coverageBefore"]["pedigreeComplete"] == 0
    assert audit["coverageAfter"]["pedigreeComplete"] == 1
    assert audit["providerOutcomes"]["licensed_test:pedigree"]["withData"] == 1


def test_unknown_circuit_cannot_default_to_local_provider():
    reg = DataBankRegistry()
    def forbidden(*args):
        raise AssertionError("unknown circuit was sent to NAR")
    reg.register(DataSource("local", "NAR", 10, SourceCapabilities(pedigree=True), {"pedigree": forbidden}))
    out = asyncio.run(enrich_race_missing({"date": "2026-10-25", "horses": [{"horseNumber": 1}]}, bank_registry=reg))
    assert out["preparedMeta"]["supplementalSearch"]["status"] == "unknown-circuit"


def test_history_requires_valid_prior_dates_in_every_short_history_merge():
    rows = [{"date": "2026/10/24", "track": "京都", "distance": 1200},
            {"date": "2026/10/25"}, {"date": "2026-10-26"},
            {"date": "bad"}, {"finish": 1}]
    out = _merge_runs([], rows, cutoff="2026-10-25")
    assert len(out) == 1
    assert out[0]["date"] == "2026-10-24"
    assert _merge_runs([], rows, cutoff="bad") == []


def test_existing_app_enrichment_uses_same_non_overwriting_merge():
    # Exercise the existing function without starting the network-heavy app.
    import ast
    from pathlib import Path
    tree = ast.parse(Path("app.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_merge_enrichment")
    namespace = {"_strip_excluded": lambda value: value}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    for key in ("smartRows", "netkeibaRows", "extra"):
        horse = {"horseNumber": 1, "name": "馬", "pedigree": {"sire": "公式父"}}
        row = {"horseNumber": 1, "name": "馬", "pedigree": {"sire": "別父", "dam": "母"}}
        data = {key: [row]} if key != "extra" else {key: [{"source": "contract", "rows": [dict(row, extra=row)]}]}
        out = namespace["_merge_enrichment"]({"circuit": "中央", "horses": [horse]}, data)
        assert out["horses"][0]["pedigree"] == {"sire": "公式父", "dam": "母"}


def test_storage_filter_keeps_requested_training_evidence_without_reviving_scores():
    import ast
    from arvexq.domain.legacy_evaluation import SOURCE
    tree = ast.parse(SOURCE)
    f = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_excluded")
    ns = {}
    exec(compile(ast.Module(body=[f], type_ignores=[]), "legacy_evaluation.py", "exec"), ns)
    original = {"horses": [{"training": [{"date": "2026-10-20", "seconds": 52.1}],
                            "workouts": [{"source": "licensed"}], "trainingComment": "観測",
                            "調教": {"source": "official"}, "trainingScore": 99}]}
    before = copy.deepcopy(original)
    out = ns["_strip_excluded"](original)
    assert out["horses"][0]["training"] == original["horses"][0]["training"]
    assert "trainingScore" not in out["horses"][0]
    assert all(k in out["horses"][0] for k in ("workouts", "trainingComment", "調教"))
    assert original == before
