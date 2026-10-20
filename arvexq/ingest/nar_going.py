"""NAR going extraction, including observed Banei track moisture."""
import re
from arvexq.components.item_001.environment_values import _env_clean_condition

def parse_nar_going(text: str) -> str | None:
    match = re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)", text or "")
    return _env_clean_condition(match.group(1)) if match else None


def parse_nar_going_moisture(text: str) -> str | None:
    """Return observed Banei 馬場水分 without converting it to flat going."""
    match = re.search(r"(?:^|[\s　])馬場(?!状態)\s*[：:]\s*(\d+(?:\.\d+)?)", text or "")
    return match.group(1) if match else None
