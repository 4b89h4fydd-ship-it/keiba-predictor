"""Independent #62: timezone-explicit acquisition instant for observed market odds."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

TOKYO=ZoneInfo("Asia/Tokyo")

def odds_observed_at(value=None):
    """Provider/scheduler observation time; do not infer market time from race start."""
    time=value if value is not None else datetime.now(timezone.utc)
    if time.tzinfo is None:raise ValueError("odds acquisition instant must include timezone")
    return time.astimezone(TOKYO).strftime("%H:%M:%S")
