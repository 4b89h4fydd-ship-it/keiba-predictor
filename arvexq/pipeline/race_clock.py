"""Independent race time conversion for track weather updates."""
import re

def _race_minutes_server(row:dict)->int:
    m=re.match(r"^(\d{1,2}):(\d{2})",str(row.get("startTime") or row.get("scheduledStartTime") or ""))
    return int(m.group(1))*60+int(m.group(2)) if m else 9999

