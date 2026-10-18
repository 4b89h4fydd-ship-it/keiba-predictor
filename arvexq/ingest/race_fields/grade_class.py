"""Observed JRA race grade/class, never inferred from horse performance."""
import re

_GRADE = re.compile(r"(?<![A-Za-z0-9])(?:Jpn|G)\\s*([1-3ⅠⅡⅢ]|II|III)(?![A-Za-z0-9])", re.I)
_CLASS = re.compile(r"(?:[1-3]勝クラス|新馬|未勝利|オープン|OP)(?![A-Za-z0-9])",re.I)
_ROMAN = {"Ⅰ":"1","Ⅱ":"2","Ⅲ":"3","I":"1","II":"2","III":"3"}

def extract(text):
    """Return observed (grade, class); no grade/class becomes empty strings."""
    value = str(text or "")
    grade_match = _GRADE.search(value)
    grade = ""
    if grade_match:
        prefix = "Jpn" if grade_match.group(0).lower().startswith("jpn") else "G"
        grade = prefix + _ROMAN.get(grade_match.group(1).upper(), "")
    class_match = _CLASS.search(value)
    race_class = class_match.group(0).upper() if class_match else ""
    return grade, race_class
