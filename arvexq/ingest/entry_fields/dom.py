"""Shared DOM access only; field interpretation belongs to the field modules."""
from arvexq.ingest.field_normalization import _clean

def text(node):
    return _clean(node.get_text(" ", strip=True)) if node is not None else ""

def horse_info(row):
    return row.select_one("td.Horse_Info") or row.select_one("td.HorseInfo")

def age_text(row):
    info = horse_info(row)
    for node in (row.select_one("span.Barei"), row.select_one("td.Barei"),
                 info.select_one("dd.Age") if info is not None else None):
        if text(node): return text(node)
    return ""

def weight_text(row):
    info = horse_info(row)
    return text(row.select_one("td.Weight")) or text(info.select_one("div.Weight") if info is not None else None)
