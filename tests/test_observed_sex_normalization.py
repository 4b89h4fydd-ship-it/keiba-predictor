"""Independent observed-sex contract tests (no app boot)."""
from arvexq.components.runtime import composed_app_source
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

def test_all_race_readback_paths_keep_missing_sex():
    """Guard app's normal/fast and legacy readback paths from male fallbacks."""
    from pathlib import Path
    from arvexq.infra.legacy_stores import SOURCE

    app_source = composed_app_source()
    assert app_source.count('"sex":e["sex"] or ""') == 2
    assert '"sex":e["sex"] or "牡"' not in app_source
    assert '"sex": e["sex"] or ""' in SOURCE
    assert '"sex": e["sex"] or "牡"' not in SOURCE
    assert "sex TEXT NOT NULL DEFAULT ''" in SOURCE

def test_fast_nar_readback_from_real_sqlite(tmp_path, monkeypatch):
    """Execute the app fast path against SQLite, not just source assertions."""
    import sqlite3
    import app

    path = tmp_path / "race.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE races (
            track TEXT, date TEXT, race_no INTEGER, title TEXT, distance INTEGER,
            condition TEXT, weather TEXT, field_size INTEGER, prize1 INTEGER,
            start_time TEXT, scheduled_start_time TEXT)""")
        db.execute("""CREATE TABLE entries (
            track TEXT, date TEXT, race_no INTEGER, horse_no INTEGER,
            frame_no INTEGER, name TEXT, sex TEXT NOT NULL DEFAULT '',
            age INTEGER, carried_weight REAL, jockey TEXT, trainer TEXT,
            status TEXT, finish INTEGER, corner_positions_json TEXT, time_seconds REAL)""")
        db.execute("INSERT INTO races VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("園田", "2026-10-18", 1, "確認", 1400, "良", "晴", 2, 100, "10:00", "10:00"))
        for no, sex in ((1, ""), (2, "牝")):
            db.execute("""INSERT INTO entries
                (track,date,race_no,horse_no,frame_no,name,sex,age,carried_weight,
                 jockey,trainer,status,finish,corner_positions_json,time_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("園田", "2026-10-18", 1, no, no, f"馬{no}", sex, 4, 54.0,
                 "騎手", "調教師", "", 0, "[]", 0.0))
    monkeypatch.setattr(app, "DB_PATH", path)
    result = app._fast_local_race_detail("nar-2026-10-18-園田-01")
    assert result is not None
    assert [(h["horseNumber"], h["sex"]) for h in result["horses"]] == [(1, ""), (2, "牝")]

    class ReadOnlyNarStore:
        def __init__(self):
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row

        def stats(self, *args):
            return {}

        def role_profile(self, *args):
            return {}

        def prize_before(self, *args):
            return 0

        def recent_races(self, *args):
            return []

    monkeypatch.setattr(app, "NarStore", ReadOnlyNarStore)
    normal = app.nar_race_detail("nar-2026-10-18-園田-01")
    assert normal is not None
    assert [(h["horseNumber"], h["sex"]) for h in normal["horses"]] == [(1, ""), (2, "牝")]

def test_legacy_store_races_json_reads_missing_sex(tmp_path, monkeypatch):
    """Exercise original installed NarStore readback on a real isolated SQLite file."""
    import app

    store = app.NarStore(path=tmp_path / "nar-store.sqlite")
    try:
        store.conn.execute("""INSERT INTO races(track,date,race_no,title,distance,weather,condition,field_size)
                              VALUES (?,?,?,?,?,?,?,?)""",
                           ("園田", "2026-10-18", 1, "観測確認", 1400, "晴", "良", 2))
        for no, sex in ((1, ""), (2, "牝")):
            store.conn.execute("""INSERT INTO entries(track,date,race_no,horse_no,frame_no,name,sex)
                                  VALUES (?,?,?,?,?,?,?)""",
                               ("園田", "2026-10-18", 1, no, no, f"馬{no}", sex))
        store.conn.commit()
        monkeypatch.setattr(store, "stats", lambda *args: {})
        monkeypatch.setattr(store, "role_profile", lambda *args: {})
        monkeypatch.setattr(store, "prize_before", lambda *args: 0)
        monkeypatch.setattr(store, "recent_races", lambda *args: [])
        races = store.races_json("2026-10-18")
        assert len(races) == 1
        assert [(h["horseNumber"], h["sex"]) for h in races[0]["horses"]] == [(1, ""), (2, "牝")]
    finally:
        store.conn.close()
