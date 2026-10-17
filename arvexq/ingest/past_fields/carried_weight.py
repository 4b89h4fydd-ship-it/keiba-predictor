"""52: Observed jockey carried weight in kilograms."""
import re

def extract_carried_weight(text):
    m=re.search(r"(\d{2}(?:\.\d)?)\s*kg",text or "")
    return float(m.group(1)) if m else 0.0
