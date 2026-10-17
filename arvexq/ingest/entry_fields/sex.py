"""Extract and normalize only sex from a provider row. Missing values remain absent."""
import re
from .dom import age_text

def extract(row):
    match = re.match(r"^(牡|牝|セ|騸)\s*\d{1,2}", age_text(row))
    return match.group(1) if match else ""
