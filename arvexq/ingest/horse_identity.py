"""Horse name identity canonicalization for JRA/NAR matching."""
import re
from arvexq.components.item_040.field_normalization import _clean

def _horse_key(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", _clean(str(value or "")))
