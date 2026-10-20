"""Independent observed first-corner quartiles; unknown stays unknown."""
from collections import Counter
import math


def style_field(histories, window=None):
    if window not in (None, 5):
        raise ValueError("unsupported style window")
    result = {}
    for no, rows in histories.items():
        counts = Counter()
        for row in rows[:window]:
            corners = row.get("cornerPositions") or row.get("passing") or []
            n = row.get("fieldSize")
            if not isinstance(corners, list) or not corners or type(n) is not int or n < 3:
                continue
            x = corners[0]
            if type(x) not in (int,float) or not math.isfinite(x) or not 1 <= x <= n:
                continue
            counts[min(3, int((x-1)/(n-1)*4))] += 1
        total = sum(counts.values())
        result[no] = [counts[i]/total for i in range(4)] if total else None
    return result
