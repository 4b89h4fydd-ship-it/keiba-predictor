"""Extract and normalize only jockey from a provider row. Missing values remain absent."""
import re
from .dom import horse_info, text
from arvexq.components.item_040.field_normalization import _clean

def extract(row):
    info = horse_info(row)
    node = info.select_one("dd.Jockey") if info is not None else None
    value = ""
    if node is not None:
        value = text(node.find("em")) or _clean(re.sub(r"[\d.]+", " ", text(node)))
    fallback = row.select_one("td.Jockey")
    return value or (text(fallback.find("a")) if fallback is not None else "")
