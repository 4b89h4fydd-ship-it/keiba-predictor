"""Reuse verified revisions, recalculate changed inputs and dependent later races."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import zipfile

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.prediction.forecast_revisions import input_hash, originals_hash
from arvexq.prediction.learned_scenarios import race_family
from scripts.arvexq_rebuild_saved_forecasts import rebuild


def signature(raw):
    d = unpack_detail(json.loads(raw))
    extra = {k: d.get(k) for k in ('id', 'date', 'startTime', 'scheduledStartTime',
                                  'availableBetTypes', 'placePlaces', 'preOffMarket')}
    extra['runners'] = [{k: h.get(k) for k in ('horseNumber', 'scratched', 'withdrawn',
                                              'cancelled', 'status', 'frameNumber')}
                        for h in d.get('horses', [])]
    return input_hash(d), originals_hash(d), json.dumps(extra, sort_keys=True, ensure_ascii=False)


def rows(path):
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
        return dict(db.execute('SELECT race_id,payload FROM race_details'))


def prepare(old_source, current_source, output):
    output = Path(output)
    old, current = rows(old_source), rows(current_source)
    missing = sorted(set(old) - set(current))
    assert not missing, ('ORIGINAL_RACES_MISSING', missing)
    changed = [rid for rid in sorted(old) if old[rid] != current[rid]
               and signature(old[rid]) != signature(current[rid])]
    training_changed = [rid for rid in sorted(old) if old[rid] != current[rid]
                        and unpack_detail(json.loads(old[rid])).get('result') != unpack_detail(json.loads(current[rid])).get('result')]
    added = sorted(set(current) - set(old))
    # Training is strictly earlier date, circuit and family. Refresh any later
    # target whose historical training population may have changed as well.
    metadata = {rid: json.loads(raw) for rid, raw in current.items()}
    dirty = [(metadata[rid]['date'], metadata[rid].get('circuit'), race_family(metadata[rid]))
             for rid in changed + added + training_changed]
    dirty += [(d['date'], d.get('circuit'), race_family(d))
              for rid in changed + training_changed for d in [json.loads(old[rid])]]
    refresh = set(changed + added)
    for rid, d in metadata.items():
        if any(d['date'] > day and d.get('circuit') == circuit and race_family(d) == family
               for day, circuit, family in dirty):
            refresh.add(rid)
    report = {'rebuiltRaces': len(old), 'liveRaces': len(current), 'addedRaceIds': added,
              'changedForecastInputRaceIds': changed, 'changedTrainingResultRaceIds': training_changed,
              'recalculatedRaceIds': sorted(refresh)}
    (output / 'source-comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('FRESH_INPUT_RECALCULATION_SCOPE', {k: len(v) if isinstance(v, list) else v for k, v in report.items()}, flush=True)
    if not refresh:
        return report
    # Preserve the downloaded immutable ledger and its original summary first.
    ledger = output / 'revisions.sqlite3'
    shutil.copyfile(ledger, output / 'revisions-original.sqlite3')
    shutil.copyfile(output / 'rebuild-summary.json', output / 'rebuild-original-summary.json')
    summary = json.loads((output / 'rebuild-summary.json').read_text())
    expected = {Path(name).name: digest for name, digest in summary['officialNarArchiveSha256'].items()}
    archive_dir = output / 'verified-official-inputs'
    archive_dir.mkdir()
    with zipfile.ZipFile(output / 'official-nar-inputs.zip') as archive:
        for name in archive.namelist():
            basename = Path(name).name
            assert name == basename and basename in expected, 'UNRECOGNIZED_OFFICIAL_ARCHIVE'
            data = archive.read(name)
            assert hashlib.sha256(data).hexdigest() == expected[basename], 'OFFICIAL_ARCHIVE_CHANGED'
            (archive_dir / basename).write_bytes(data)
    archives = sorted(archive_dir.glob('*_race.zip'))
    assert {p.name for p in archives} == set(expected), 'OFFICIAL_ARCHIVE_MISSING'
    # Only the disposable derived ledger is changed. D1/original artifacts stay intact.
    with sqlite3.connect(ledger) as db:
        db.executemany('DELETE FROM revisions WHERE race_id=?', [(rid,) for rid in refresh])
    result = rebuild(current_source, output, training_limit=summary['trainingLimit'],
                     nar_archives=archives, only_missing=True)
    assert result['allSavedRebuilt'] and not result['errors']
    print('ALL_CURRENT_REVISIONS_PREPARED', result['revisions'], flush=True)
    return report


if __name__ == '__main__':
    prepare('/tmp/revision-original-source.sqlite3', '/tmp/arvexq-complete-d1.sqlite3', '/tmp/forecast-revisions')
