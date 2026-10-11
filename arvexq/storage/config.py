"""Existing environment/path defaults; does not construct databases."""
import os
from pathlib import Path

NAR_DAILY_RACE_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"

NAR_MONTHLY_RACE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload"
    "?type=monthly&k_year={year}&k_month={month}"
)

def _default_data_root() -> Path:
    env=os.getenv("KEIBA_DATA_DIR","").strip()
    if env:return Path(env)
    for cand in (Path("/var/data/keiba_data"),Path("/data/keiba_data")):
        try:
            if cand.parent.exists() and os.access(cand.parent,os.W_OK):
                return cand
        except Exception:pass
    return Path("/tmp/keiba_data")

DATA_ROOT = _default_data_root()

ARCHIVE_DIR = DATA_ROOT / "nar" / "archives"

DB_PATH = DATA_ROOT / "nar" / "nar.sqlite3"

PREPARED_DB_PATH = DATA_ROOT / "prepared" / "prepared.sqlite3"

RACEDB_PATH = Path(os.getenv("RACEDB_PATH", str(DATA_ROOT / "racedb" / "racedb.sqlite3")))

DAY_BUNDLE_DB_PATH = Path(os.getenv("DAY_BUNDLE_DB_PATH", str(DATA_ROOT / "bundle" / "day_bundle.sqlite3")))
CENTRAL_DB_PATH = DATA_ROOT / "central" / "central.sqlite3"
