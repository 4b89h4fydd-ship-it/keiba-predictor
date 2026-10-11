"""nar/imports.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import time
from arvexq.storage.policies.archive import retain_archive_rows
from arvexq.storage.sqlite.transactions import begin_write
from pathlib import Path
from typing import Iterable
from arvexq.storage.nar.contracts import RaceRow
from arvexq.storage.nar.contracts import EntryRow

class NarImports:
    def import_rows(self, races: Iterable[RaceRow], entries: Iterable[EntryRow]) -> None:
        races = list(races)
        with self.conn:
            begin_write(self.conn)
            races, entries = retain_archive_rows(self.conn, races, list(entries))
            race_lookup = {(r.track, r.date, r.race_no): r for r in races}
            for r in races:
                self.conn.execute(
                    """
                    INSERT INTO races(track,date,race_no,start_time,scheduled_start_time,title,distance,weather,condition,field_size,
                                      prize1,prize2,prize3,prize4,prize5,corners_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(track,date,race_no) DO UPDATE SET
                      start_time=excluded.start_time,title=excluded.title,distance=excluded.distance,
                      weather=CASE WHEN excluded.weather NOT IN ('','不明') THEN excluded.weather ELSE races.weather END,
                      condition=CASE WHEN excluded.condition NOT IN ('','不明') THEN excluded.condition ELSE races.condition END,
                      field_size=excluded.field_size,
                      prize1=excluded.prize1,prize2=excluded.prize2,prize3=excluded.prize3,
                      prize4=excluded.prize4,prize5=excluded.prize5,corners_json=excluded.corners_json
                    """,
                    (
                        r.track, r.date, r.race_no, r.start_time, r.start_time, r.title, r.distance, r.weather, r.condition,
                        r.field_size, *r.prize,
                        json.dumps([{str(k): v for k, v in c.items()} for c in r.corners], ensure_ascii=False),
                    ),
                )
            for e in entries:
                race = race_lookup.get((e.track, e.date, e.race_no))
                corners: list[int] = []
                if race:
                    for c in race.corners:
                        if e.horse_no in c:
                            corners.append(c[e.horse_no])
                self.conn.execute(
                    """
                    INSERT INTO entries(track,date,race_no,frame_no,horse_no,name,sex,age,carried_weight,
                                        jockey,trainer,status,finish,time_seconds,corner_positions_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(track,date,race_no,horse_no) DO UPDATE SET
                      frame_no=excluded.frame_no,name=excluded.name,sex=excluded.sex,age=excluded.age,
                      carried_weight=excluded.carried_weight,jockey=excluded.jockey,trainer=excluded.trainer,
                      status=CASE WHEN entries.status<>'' THEN entries.status ELSE excluded.status END,
                      finish=excluded.finish,time_seconds=excluded.time_seconds,
                      corner_positions_json=excluded.corner_positions_json
                    """,
                    (
                        e.track, e.date, e.race_no, e.frame_no, e.horse_no, e.name, e.sex, e.age,
                        e.carried_weight, e.jockey, e.trainer, "", e.finish, e.time_seconds,
                        json.dumps(corners, ensure_ascii=False),
                    ),
                )


    def mark_synced(self, cache_key: str, archive_path: Path) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO sync_log(cache_key,synced_at,archive_path) VALUES(?,?,?)",
                (cache_key, int(time.time()), str(archive_path)),
            )


    def synced_at(self, cache_key: str) -> int | None:
        row = self.conn.execute("SELECT synced_at FROM sync_log WHERE cache_key=?", (cache_key,)).fetchone()
        return int(row[0]) if row else None

