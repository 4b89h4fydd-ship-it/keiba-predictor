"""43: Historical venue. Track names are supplied by the provider adapter."""
import re

def extract_track(text, tracks):
    for track in tracks:
        if re.search(r"(?:日|\s)"+re.escape(track)+r"(?:\s|$)",text or ""):
            return track
    return ""
