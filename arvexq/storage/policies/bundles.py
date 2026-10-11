"""Prevent a failed day refresh from replacing a richer persisted bundle."""
from arvexq.storage.sqlite.transactions import begin_write


def accept_bundle(conn, race_date, payload, complete):
    begin_write(conn)
    previous=conn.execute('SELECT race_count,detail_count FROM day_bundles WHERE race_date=?',
                          (race_date,)).fetchone()
    if not previous or complete:
        return True
    return int(payload.get('raceCount') or 0)>=int(previous[0]) \
        and int(payload.get('detailCount') or 0)>=int(previous[1])
