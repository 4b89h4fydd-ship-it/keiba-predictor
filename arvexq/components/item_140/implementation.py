"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _default_data_root() -> Path:
    env=os.getenv("KEIBA_DATA_DIR","").strip()
    if env:return Path(env)
    for cand in (Path("/var/data/keiba_data"),Path("/data/keiba_data")):
        try:
            if cand.parent.exists() and os.access(cand.parent,os.W_OK):
                return cand
        except Exception:pass
    return Path("/tmp/keiba_data")

@dataclass
class RaceRow:
    track: str
    date: str
    race_no: int
    start_time: str
    title: str
    distance: int
    weather: str
    condition: str
    field_size: int
    prize: tuple[int, int, int, int, int]
    corners: list[dict[int, int]]

@dataclass
class EntryRow:
    track: str
    date: str
    race_no: int
    frame_no: int
    horse_no: int
    name: str
    sex: str
    age: int
    carried_weight: float
    jockey: str
    trainer: str
    finish: int
    time_seconds: float

def _new_conn(path: Path):
    conn = sqlite3.connect(path, timeout=1.5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=1200")
    except Exception:
        pass
    return conn
