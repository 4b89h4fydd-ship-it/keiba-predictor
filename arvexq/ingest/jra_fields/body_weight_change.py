"""JRA official race-card body weight delta, only when explicitly printed."""
import re


def extract(info_text: str) -> int | None:
    full = re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]", info_text)
    if full:
        try:
            return int(full.group(2))
        except (ValueError, TypeError):
            pass
    return None
