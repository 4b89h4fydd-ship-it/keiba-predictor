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

def test_provider_dom_to_sqlite_without_inferred_male(tmp_path):
    """Check observed and missing DOM sex through parsing and persistent storage."""
    import sqlite3
    from bs4 import BeautifulSoup
    from arvexq.ingest.entry_fields.netkeiba import parse_row

    def parse(html):
        return parse_row(BeautifulSoup(html, "html.parser").find("tr"))

    observed = parse('<tr><td class="Umaban">1</td><td class="Horse_Info"><dt class="Horse"><a>牝馬</a></dt><dd class="Age">牝4</dd></td></tr>')
    missing = parse('<tr><td class="Umaban">2</td><td class="Horse_Info"><dt class="Horse"><a>不明馬</a></dt></td></tr>')
    assert observed["sex"] == "牝"
    assert missing["sex"] == ""

    with sqlite3.connect(tmp_path / "provider.sqlite") as db:
        db.execute("CREATE TABLE entries(horse_no INTEGER PRIMARY KEY, sex TEXT NOT NULL DEFAULT '')")
        for horse in (observed, missing):
            db.execute("INSERT INTO entries(horse_no, sex) VALUES (?, ?)",
                       (horse["horseNumber"], _normalize_sex(horse["sex"])))
        assert db.execute("SELECT sex FROM entries ORDER BY horse_no").fetchall() == [("牝",), ("",)]
