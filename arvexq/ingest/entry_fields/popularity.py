"""Extract and normalize only popularity from a provider row. Missing values remain absent."""
import re
from .dom import text

def extract(row):
    match = re.search(r"\d+", text(row.find("span", id=re.compile(r"^ninki-1_"))))
    return int(match.group()) if match else None
