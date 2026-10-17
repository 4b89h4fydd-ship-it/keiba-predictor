"""Contract tests for isolated official NAR CSV decoding."""
import io
import zipfile
from arvexq.ingest.nar_csv import RACE_IDX, HORSE_IDX, _stable_id, read_csv_from_zip, strip_header

def test_schema_indexes():
    assert RACE_IDX["distance"] == 23
    assert HORSE_IDX["horse_no"] == 5
    assert _stable_id("nar", "2026-10-17", 1) == _stable_id("nar", "2026-10-17", 1)

def test_zip_csv_and_header():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as archive:
        archive.writestr("races.csv", "競馬場,番号\n園田,1\n")
    parsed = read_csv_from_zip(raw.getvalue(), ".csv")
    assert strip_header(parsed) == [["園田", "1"]]
    assert read_csv_from_zip(raw.getvalue(), ".txt") == []
