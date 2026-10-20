"""45: Historical ground going, never inferred from the target race."""

def extract_going(text):
    for going in ("不良","稍重","重","良"):
        if going in (text or ""): return going
    return "不明"
