"""48: Observed historical finishing time in seconds."""
import re

def extract_time_seconds(text):
    m=re.search(r"(?<!\d)(\d{1,2}):(\d{2}\.\d)(?!\d)",text or "")
    return int(m.group(1))*60+float(m.group(2)) if m else 0.0
