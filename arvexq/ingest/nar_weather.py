"""NAR weather extraction. Does not parse going or scratches."""
import re
from arvexq.components.item_001.environment_values import _env_clean_weather

def parse_nar_weather(text: str) -> str | None:
    match = re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)", text or "")
    return _env_clean_weather(match.group(1)) if match else None
