from arvexq.ingest.nar_csv import canonical_race_id,same_race

def test_official_ids_normalize_only_complete_identity():
    assert canonical_race_id("地方","2026/10/18","大井","3")=="nar-2026-10-18-大井-03"
    assert canonical_race_id("JRA","2026-10-18","京都",12)=="jra-2026-10-18-京都-12"
    for values in [("NAR","2026-02-30","大井",1),("JRA","2026-10-18","",1),("NAR","2026-10-18","大井",13),("unknown","2026-10-18","大井",1)]:
        assert canonical_race_id(*values) is None

def test_collision_and_cross_circuit_mismatch():
    one={"circuit":"NAR","date":"2026-10-18","track":"大井","raceNumber":1}
    two={"circuit":"地方","date":"2026/10/18","track":"大井","raceNumber":"01"}
    three={"circuit":"JRA","date":"2026-10-18","track":"大井","raceNumber":1}
    assert same_race(one,two)
    assert not same_race(one,three)
    assert not same_race(one,{"circuit":"NAR","date":"2026-10-18","track":"大井"})
