#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path('arvexq/prediction/mass_feature_factory.py')
text = PATH.read_text(encoding='utf-8')

import_anchor = 'from typing import Any, Callable, Iterable\n'
import_line = 'from arvexq.prediction.jra_class_evidence import class_ordinal\n'
if import_line not in text:
    if import_anchor not in text:
        raise SystemExit('mass feature import anchor not found')
    text = text.replace(import_anchor, import_anchor + '\n' + import_line, 1)

old_late = '''def _late_speed(run: dict[str, Any]) -> float | None:
    return _f(
        run.get(
            "last3FIndex",
            run.get("sectionalIndex", run.get("closingIndex", run.get("lateSpeedIndex"))),
        )
    )
'''
new_late = '''def _late_speed(run: dict[str, Any]) -> float | None:
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
if old_late in text:
    text = text.replace(old_late, new_late, 1)
elif 'Prefer race-relative JRA closing evidence' not in text:
    raise SystemExit('mass late-speed anchor not found')

old_level = '''def _opponent_level(run: dict[str, Any]) -> float | None:
    return _f(run.get("opponentLevel", run.get("levelScore", run.get("raceLevel"))))
'''
new_level = '''def _opponent_level(run: dict[str, Any]) -> float | None:
    direct = _f(run.get("opponentLevel", run.get("levelScore", run.get("raceLevel"))))
    if direct is not None and direct > 0:
        return direct
    # Class parsed from the historical race title is a candidate ML feature only.
    # It is not promoted into the production four-pillar marks after the challenger
    # showed no win-rate gain.
    parsed = class_ordinal(run.get("title") or run.get("raceName"))
    return float(parsed) if parsed is not None else None
'''
if old_level in text:
    text = text.replace(old_level, new_level, 1)
elif 'Class parsed from the historical race title is a candidate ML feature only.' not in text:
    raise SystemExit('mass opponent-level anchor not found')

PATH.write_text(text, encoding='utf-8')
print('mass feature JRA contextual evidence wired')
