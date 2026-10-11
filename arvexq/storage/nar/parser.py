"""nar/parser.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
from arvexq.storage.nar.contracts import RaceRow, EntryRow, RACE_IDX, HORSE_IDX
from arvexq.normalize.scalars import _int, _carried_weight, _clean, _iso_date, _normalize_condition, _normalize_sex, _normalize_weather, _start_time, _time_seconds
from arvexq.ingest.parsers.nar_archive import parse_corner_order, read_csv_from_zip, strip_header


class NarArchiveParser:
    def parse(self, zip_bytes: bytes) -> tuple[list[RaceRow], list[EntryRow]]:
        race_rows = strip_header(read_csv_from_zip(zip_bytes, "_racelist.csv"))
        horse_rows = strip_header(read_csv_from_zip(zip_bytes, "_horselist.csv"))

        races: list[RaceRow] = []
        for row in race_rows:
            if len(row) < 33:
                continue
            corner_orders: list[dict[int, int]] = []
            for i in range(8):
                idx = RACE_IDX["corner_order_start"] + i
                if idx < len(row) and _clean(row[idx]):
                    corner_orders.append(parse_corner_order(row[idx]))
            races.append(
                RaceRow(
                    track=_clean(row[RACE_IDX["track"]]),
                    date=_iso_date(row[RACE_IDX["date"]]),
                    race_no=_int(row[RACE_IDX["race_no"]]),
                    start_time=_start_time(row[RACE_IDX["start_time"]]),
                    title=_clean(row[RACE_IDX["title"]]),
                    distance=_int(row[RACE_IDX["distance"]]),
                    weather=_normalize_weather(row[RACE_IDX["weather"]]),
                    condition=_normalize_condition(row[RACE_IDX["condition"]]),
                    field_size=_int(row[RACE_IDX["field_size"]]),
                    prize=tuple(_int(row[RACE_IDX[f"prize{i}"]]) for i in range(1, 6)),
                    corners=corner_orders,
                )
            )

        entries: list[EntryRow] = []
        for row in horse_rows:
            if len(row) < 19:
                continue
            entries.append(
                EntryRow(
                    track=_clean(row[HORSE_IDX["track"]]),
                    date=_iso_date(row[HORSE_IDX["date"]]),
                    race_no=_int(row[HORSE_IDX["race_no"]]),
                    frame_no=_int(row[HORSE_IDX["frame_no"]]),
                    horse_no=_int(row[HORSE_IDX["horse_no"]]),
                    name=_clean(row[HORSE_IDX["name"]]),
                    sex=_normalize_sex(row[HORSE_IDX["sex"]]),
                    age=_int(row[HORSE_IDX["age"]]),
                    jockey=_clean(row[HORSE_IDX["jockey"]]),
                    carried_weight=_carried_weight(row[HORSE_IDX["carried_weight"]]),
                    trainer=_clean(row[HORSE_IDX["trainer"]]),
                    finish=_int(row[HORSE_IDX["finish"]]) if len(row) > HORSE_IDX["finish"] else 0,
                    time_seconds=_time_seconds(row[HORSE_IDX["time"]]) if len(row) > HORSE_IDX["time"] else 0,
                )
            )
        return races, entries

