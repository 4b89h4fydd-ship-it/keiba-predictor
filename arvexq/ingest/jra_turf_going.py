"""JRA turf-going extraction only."""
import re
from arvexq.components.item_001.environment_values import _env_clean_condition

def parse_jra_turf_going(text: str) -> str | None:
    match = re.search(r"芝\s*[：:]?\s*(不良|稍重|重|良)", text or "")
    return _env_clean_condition(match.group(1)) if match else None
