from arvexq.ingest.horse_identity import _horse_key

def test_horse_identity_normalization():
    assert _horse_key(" ディープ　インパクト ") == "ディープインパクト"
    assert _horse_key(None) == ""
    assert _horse_key("A B") == "AB"
