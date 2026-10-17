"""#73 Strict confirmed race result from explicit official declaration."""
import re

def official_confirmed(text):
    s=str(text or "")
    return bool(re.search(r"確定",s)) and not bool(re.search(r"速報|暫定",s))
