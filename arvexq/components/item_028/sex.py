"""Extract and normalize only observed sex values. Missing values remain absent."""
import re


def normalize(value):
    """Do not infer male sex from missing or unknown data."""
    s = str(value or "").strip().replace("\u3000", " ")
    if s in {"牡", "牝"}:
        return s
    if s in {"セ", "セン", "騸"}:
        return "セ"
    return ""


def extract(row):
    # Avoid sex -> dom -> field_normalization -> sex import cycle.
    from arvexq.ingest.entry_fields.dom import age_text

    match = re.match(r"^(牡|牝|セ|騸)\s*\d{1,2}", age_text(row))
    return normalize(match.group(1)) if match else ""
