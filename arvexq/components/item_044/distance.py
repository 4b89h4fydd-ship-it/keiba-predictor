"""44: Historical trip in metres."""
import re

def extract_distance(text):
    m=re.search(r"(\d{3,4})(芝|ダ|障)",text or "")
    return int(m.group(1)) if m else 0

def extract_surface(text):
    m=re.search(r"(\d{3,4})(芝|ダ|障)",text or "")
    return m.group(2) if m else ""
