"""Independent observed-sex contract tests (no app boot)."""
import pytest

from arvexq.ingest.entry_fields.sex import normalize
from arvexq.ingest.field_normalization import _normalize_sex


@pytest.mark.parametrize("raw,expected", [
    ("牡", "牡"), ("牝", "牝"), ("セ", "セ"),
    ("セン", "セ"), ("騸", "セ"), (" 牡 ", "牡"),
    ("　牝　", "牝"), ("", ""), (None, ""),
    ("不明", ""), ("-", ""), ("?", ""),
    ("雄", ""), ("雌", ""), ("牡3", ""),
])
def test_observed_sex_contract(raw, expected):
    assert normalize(raw) == expected
    assert _normalize_sex(raw) == expected

def test_sqlite_preserves_unknown_sex_as_empty(tmp_path):
    """Exercise the ingestion normalizer through a SQLite round trip."""
    import sqlite3

    db = sqlite3.connect(tmp_path / "observed-sex.sqlite")
    try:
        db.execute("CREATE TABLE entries (horse_no INTEGER PRIMARY KEY, sex TEXT NOT NULL DEFAULT '')")
        for horse_no, observed in enumerate(("牡", "牝", "セ", "", None, "不明"), start=1):
            db.execute("INSERT INTO entries (horse_no, sex) VALUES (?, ?)", (horse_no, _normalize_sex(observed)))
        db.execute("INSERT INTO entries (horse_no) VALUES (7)")
        db.commit()
        actual = [row[0] for row in db.execute("SELECT sex FROM entries ORDER BY horse_no")]
        assert actual == ["牡", "牝", "セ", "", "", "", ""]
    finally:
        db.close()
