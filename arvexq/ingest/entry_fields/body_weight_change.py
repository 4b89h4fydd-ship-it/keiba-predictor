"""Extract and normalize only body_weight_change from a provider row. Missing values remain absent."""
import re
from .dom import weight_text

def extract(row):
    match = re.search(r"\d{3}\s*[（(]\s*([+\-]?\d+)\s*[）)]", weight_text(row))
    return int(match.group(1)) if match else None


def normalize(value):
    """Observed delta -> integer kg / None; zero is a known observation."""
    try:
        change = int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError, OverflowError):
        change = None
    return change if change is not None and abs(change) <= 99 else None
