"""Extract and normalize only age from a provider row. Missing values remain absent."""
import re
from arvexq.ingest.entry_fields.dom import age_text

def extract(row):
    match = re.match(r"^(?:牡|牝|セ|騸)\s*(\d{1,2})", age_text(row))
    return int(match.group(1)) if match else 0
