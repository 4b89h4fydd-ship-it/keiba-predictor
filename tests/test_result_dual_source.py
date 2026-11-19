"""Dual-source result merge (official primary, netkeiba secondary)."""
from arvexq.ingest.result_dual_source import merge_result_sources, result_gaps


def _fin(no, **kw):
    base = {
        "finish": 1, "finishLabel": "1着", "horseNumber": no, "frameNumber": 1,
        "name": "テスト", "timeSeconds": 93.0, "marginText": "",
        "cornerPositions": [1, 1], "bodyWeight": 460, "bodyWeightChange": 0,
        "popularity": 1, "winOdds": 2.0, "last3FSeconds": 39.0,
    }
    base.update(kw)
    return base


def _result(source, finishers, **kw):
    out = {"status": "確定", "finishers": finishers, "source": source,
           "payouts": [{"type": "単勝"}]}
    out.update(kw)
    return out


def test_fills_missing_fields_from_secondary():
    official = _result("NAR公式競走成績", [
        _fin(1, last3FSeconds=None, cornerPositions=[]),
        _fin(2, finish=2, bodyWeight=None),
    ], raceLapTimes=[])
    official["payouts"] = []
    nk = _result("netkeiba結果", [
        _fin(1, last3FSeconds=38.5, cornerPositions=[3, 1]),
        _fin(2, finish=2, bodyWeight=455, bodyWeightChange=-5),
    ], raceLapTimes=[13.8, 12.2])
    merged = merge_result_sources(official, nk)
    f1, f2 = merged["finishers"]
    assert f1["last3FSeconds"] == 38.5
    assert f1["last3fSeconds"] == 38.5  # both spellings filled
    assert f1["cornerPositions"] == [3, 1]
    assert f2["bodyWeight"] == 455
    assert merged["raceLapTimes"] == [13.8, 12.2]
    assert merged["payouts"] == [{"type": "単勝"}]
    meta = merged["dualSource"]
    assert meta["primary"] == "NAR公式競走成績"
    assert meta["filled"]["last3FSeconds"] == 1
    assert meta["filled"]["cornerPositions"] == 1
    assert meta["filledTotal"] >= 4
    assert meta["conflictCount"] == 0
    # Inputs are not mutated.
    assert official["finishers"][0]["last3FSeconds"] is None


def test_official_value_wins_and_conflict_is_recorded():
    official = _result("JRA公式", [_fin(1, timeSeconds=93.0)])
    nk = _result("netkeiba結果", [_fin(1, timeSeconds=94.2)])
    merged = merge_result_sources(official, nk)
    assert merged["finishers"][0]["timeSeconds"] == 93.0
    meta = merged["dualSource"]
    assert meta["conflictCount"] == 1
    assert meta["conflicts"][0]["field"] == "timeSeconds"
    assert meta["conflicts"][0]["official"] == 93.0
    assert meta["conflicts"][0]["netkeiba"] == 94.2


def test_margin_notation_variants_are_not_conflicts():
    official = _result("公式", [
        _fin(1, marginText="大差"),
        _fin(2, finish=2, marginText="1 3/4"),
        _fin(3, finish=3, marginText="クビ"),
        _fin(4, finish=4, marginText="３ 1/2"),
        _fin(5, finish=5, marginText="１／２"),
        _fin(6, finish=6, marginText="４"),
    ])
    nk = _result("netkeiba結果", [
        _fin(1, marginText="大"),
        _fin(2, finish=2, marginText="1.3/4"),
        _fin(3, finish=3, marginText="クビ"),
        _fin(4, finish=4, marginText="3.1/2"),
        _fin(5, finish=5, marginText="1/2"),
        _fin(6, finish=6, marginText="4"),
    ])
    merged = merge_result_sources(official, nk)
    assert merged["dualSource"]["conflictCount"] == 0


def test_corner_length_difference_is_coverage_not_conflict():
    official = _result("公式", [_fin(1, cornerPositions=[7, 7, 8, 8, 5, 4])])
    nk = _result("netkeiba結果", [_fin(1, cornerPositions=[8, 8])])
    merged = merge_result_sources(official, nk)
    meta = merged["dualSource"]
    assert meta["conflictCount"] == 0
    assert meta["cornerCoverageDiffs"] == 1
    # Official corners are kept as-is.
    assert merged["finishers"][0]["cornerPositions"] == [7, 7, 8, 8, 5, 4]


def test_corner_none_slots_filled_when_lengths_match():
    official = _result("公式", [_fin(1, cornerPositions=[8, None, 2])])
    nk = _result("netkeiba結果", [_fin(1, cornerPositions=[8, 7, 2])])
    merged = merge_result_sources(official, nk)
    assert merged["finishers"][0]["cornerPositions"] == [8, 7, 2]
    assert merged["dualSource"]["filled"]["cornerPositions"] == 1


def test_secondary_only_rows_are_not_added():
    # netkeiba lists the scratched horse as a finish=0 row; the
    # official table accounts for it outside the finishers, so the
    # row must not become a finisher.
    official = _result("公式", [_fin(1), _fin(2, finish=2)])
    nk = _result("netkeiba結果", [
        _fin(1), _fin(2, finish=2),
        _fin(3, finish=0, finishLabel="取消", timeSeconds=0.0),
    ])
    merged = merge_result_sources(official, nk)
    assert [f["horseNumber"] for f in merged["finishers"]] == [1, 2]


def test_finish_is_never_filled_from_secondary():
    official = _result("公式", [_fin(1, finish=0, finishLabel="中止")])
    nk = _result("netkeiba結果", [_fin(1, finish=5)])
    merged = merge_result_sources(official, nk)
    assert merged["finishers"][0]["finish"] == 0
    # Both sources recording different real placings IS a conflict.
    official2 = _result("公式", [_fin(1, finish=2)])
    nk2 = _result("netkeiba結果", [_fin(1, finish=5)])
    merged2 = merge_result_sources(official2, nk2)
    assert merged2["finishers"][0]["finish"] == 2
    assert merged2["dualSource"]["conflictCount"] == 1


def test_last3f_rank_recomputed_after_fill():
    official = _result("JRA公式", [
        _fin(1, last3FSeconds=35.0, last3FRank=1, last3FPercentile=1.0),
        _fin(2, finish=2, last3FSeconds=None),
        _fin(3, finish=3, last3FSeconds=36.0, last3FRank=2, last3FPercentile=0.0),
    ])
    nk = _result("netkeiba結果", [
        _fin(1, last3FSeconds=35.0),
        _fin(2, finish=2, last3FSeconds=34.0),
        _fin(3, finish=3, last3FSeconds=36.0),
    ])
    merged = merge_result_sources(official, nk)
    ranks = {f["horseNumber"]: f.get("last3FRank") for f in merged["finishers"]}
    assert ranks == {1: 2, 2: 1, 3: 3}


def test_single_source_passthrough():
    official = _result("公式", [_fin(1)])
    assert merge_result_sources(official, None) is official
    assert merge_result_sources(None, official) is official
    assert merge_result_sources(None, None) is None


def test_result_gaps_detection():
    complete = _result("公式", [_fin(1)], raceLapTimes=[13.0])
    assert result_gaps(complete) == []
    gappy = _result("公式", [_fin(1, last3FSeconds=None, cornerPositions=[], winOdds=None)])
    gaps = result_gaps(gappy)
    assert "last3FSeconds" in gaps
    assert "cornerPositions" in gaps
    assert "winOdds" in gaps
    assert "raceLapTimes" in gaps
    assert result_gaps(None) == ["result"]
    assert result_gaps({"finishers": []}) == ["finishers"]


def test_skip_fields_excludes_win_odds():
    official = _result("JRA公式", [_fin(1, winOdds=None)])
    nk = _result("netkeiba結果", [_fin(1, winOdds=3.5)])
    merged = merge_result_sources(official, nk, skip_fields=("winOdds",))
    assert merged["finishers"][0]["winOdds"] is None
    assert "winOdds" not in merged["dualSource"]["filled"]
