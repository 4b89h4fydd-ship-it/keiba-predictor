"""#14 JRA official announced scheduled post time."""
import re
def extract(text):
    m=re.search(r"発走時刻[：:]\s*(\d{1,2})時(\d{2})分",text or "")
    if not m:return ""
    h=int(m.group(1));minute=int(m.group(2))
    return f"{h:02d}:{minute:02d}" if h<=23 and minute<=59 else ""
