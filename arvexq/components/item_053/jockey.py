"""53: Accept only a directly labeled historical jockey; unknown stays unknown."""
import re

def extract_jockey(text):
    m=re.search(r"(?:騎手|鞍上)\s*[：:]\s*([^\s　、,()]+)",text or "")
    return m.group(1) if m else None
