"""Verify frozen research receipt integrity without promoting provenance claims."""
import json
from hashlib import sha256
from pathlib import Path


def verify_receipt(path, *, original_race=None):
    receipt = json.loads(Path(path).read_text(encoding='utf-8'))
    snapshot = receipt.get('snapshot')
    if not isinstance(snapshot, dict):
        raise ValueError('missing snapshot')
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    if sha256(raw).hexdigest() != receipt.get('snapshotSha256'):
        raise ValueError('frozen receipt checksum mismatch')
    if snapshot.get('status') != 'frozen-research-only':
        raise ValueError('not a frozen research receipt')
    if original_race is not None:
        race_raw = json.dumps(original_race, ensure_ascii=False, sort_keys=True,
                              separators=(',', ':'), allow_nan=False).encode('utf-8')
        if sha256(race_raw).hexdigest() != snapshot.get('sourceRaceSha256'):
            raise ValueError('source race checksum mismatch')
        if original_race.get('id') != snapshot.get('raceId'):
            raise ValueError('source race ID mismatch')
    return {'raceId': snapshot.get('raceId'),
            'snapshotSha256': receipt['snapshotSha256'],
            'sourceRaceSha256': snapshot.get('sourceRaceSha256'),
            'checksumVerified': True,
            'independentlyVerifiedPreoff': False,
            'note': 'Local checksum only; cannot establish trusted time or held-out training provenance.'}
