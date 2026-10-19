"""#73 Strict confirmed race result from explicit official declaration."""
import re
from arvexq.components.item_074.provisional import has_provisional_marker

def official_confirmed(text):
    s=str(text or "")
    return bool(re.search(r"確定",s)) and not has_provisional_marker(s)
