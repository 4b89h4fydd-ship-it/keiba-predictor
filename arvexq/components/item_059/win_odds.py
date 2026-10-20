"""Extract and normalize only win_odds from a provider row. Missing values remain absent."""
import re
from arvexq.ingest.entry_fields.dom import text

def extract(row):
    node = row.find("span", id=re.compile(r"^odds-1_"))
    match = re.search(r"\d+(?:\.\d+)?", text(node))
    return float(match.group()) if match else None
