"""Extract and normalize only name from a provider row. Missing values remain absent."""
from arvexq.ingest.entry_fields.dom import horse_info, text

def extract(row):
    info = horse_info(row)
    if info is None: return ""
    node = (info.select_one("dt.Horse a") or info.select_one("div.Horse02 a")
            or info.select_one("dt a") or info.select_one(".HorseName a"))
    value = text(node)
    return value if value and "のデータベース" not in value and len(value) <= 24 else ""
