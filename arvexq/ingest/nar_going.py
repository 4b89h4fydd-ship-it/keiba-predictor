"""NAR dirt-track going extraction. Independent of weather and scratches."""
import re
from arvexq.ingest.environment_values import _env_clean_condition

def parse_nar_going(text: str) -> str | None:
    match = re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)", text or "")
    return _env_clean_condition(match.group(1)) if match else None
