"""Immutable, local pre-off research ticket receipt. Not a production bet."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os

from arvexq.prediction.prerace_archive import post_at


def freeze_research_candidate(detail, plan, directory, *, captured_at=None):
    """Write a new receipt only before scheduled post; never overwrite one."""
    now = captured_at or datetime.now(timezone.utc)
    off = post_at(detail)
    if not off or now.tzinfo is None or now.utcoffset() is None or now >= off:
        raise ValueError('verified future post and timezone-aware capture required')
    race_id = detail.get('id')
    candidate = plan.get('researchLeader') if isinstance(plan, dict) else None
    if not isinstance(race_id, str) or not race_id or not isinstance(candidate, dict):
        raise ValueError('race identity and research candidate required')
    if candidate.get('status') != 'research-only-not-a-recommendation':
        raise ValueError('not a research candidate')
    if not isinstance(candidate.get('combos'), list) or not 1 <= len(candidate['combos']) <= 10:
        raise ValueError('invalid ticket count')
    snapshot = {
        'raceId': race_id, 'circuit': detail.get('circuit'),
        'capturedAt': now.isoformat(), 'scheduledOffAt': off.isoformat(),
        'candidate': candidate, 'modelVersion': plan.get('modelVersion'),
        'status': 'frozen-research-only',
        'provenanceStatus': 'locally-timestamped-not-independently-verified',
    }
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    receipt = {'snapshot': snapshot, 'snapshotSha256': sha256(raw).hexdigest()}
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    filename = sha256(race_id.encode('utf-8')).hexdigest() + '.json'
    destination = folder / filename
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(receipt, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write('\n')
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination
