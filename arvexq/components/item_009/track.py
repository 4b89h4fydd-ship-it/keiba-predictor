"""#9 JRA official venue from provider code; never infer unknown codes."""
import re
def extract(cname,codes):
    m=re.search(r"pw01dde(?:01|10)(\d{2})",cname or "")
    return codes.get(m.group(1),"") if m else ""
