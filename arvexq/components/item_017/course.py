"""#17 JRA official course descriptor. No guessed geometry."""
import re
def extract(text):
    m=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",text or "")
    return (m.group(2),int(m.group(1).replace(",",""))) if m else ("",0)
