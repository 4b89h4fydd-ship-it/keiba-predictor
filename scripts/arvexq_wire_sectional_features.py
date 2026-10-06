#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path('arvexq/prediction/mass_feature_factory.py')
text = PATH.read_text(encoding='utf-8')
old = '''def _late_speed(run: dict[str, Any]) -> float | None:
    return _f(
        run.get(
            "last3FIndex",
            run.get("sectionalIndex", run.get("closingIndex", run.get("lateSpeedIndex"))),
        )
    )
'''
new = '''def _late_speed(run: dict[str, Any]) -> float | None:
    # Prefer race-relative JRA closing evidence. Raw last3F seconds are never fed
    # directly because course/distance/going make cross-race seconds incomparable.
    direct = _f(run.get("last3FPercentile"))
    if direct is not None:
        return max(0.0, min(1.0, direct))
    rank = _f(run.get("last3FRank"))
    field = _f(run.get("fieldSize"))
    if rank is not None and field is not None and field >= 2 and 1 <= rank <= field:
        return max(0.0, min(1.0, 1.0 - (rank - 1.0) / (field - 1.0)))
    return _f(
        run.get(
            "last3FIndex",
            run.get("sectionalIndex", run.get("closingIndex", run.get("lateSpeedIndex"))),
        )
    )
'''
if old in text:
    text = text.replace(old, new, 1)
elif 'Prefer race-relative JRA closing evidence' not in text:
    raise SystemExit('mass late-speed anchor not found')
PATH.write_text(text, encoding='utf-8')
print('mass feature sectional evidence wired')
