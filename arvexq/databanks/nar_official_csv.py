"""NAR official ZIP race-list + horse-list ingestion. No automatic downloads.

CSV offsets follow https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf
Only locally provided archives are used (operator must confirm data rights).
"""
from __future__ import annotations

import csv
import io
import os
import re
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

from .registry import DataBankRegistry, DataSource, SourceCapabilities


def normalize(value):
    return "".join(unicodedata.normalize("NFKC", str(value or "")).split())


def number(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def date(value):
    x = str(value or "").replace("-", "").replace("/", "")
    return f"{x[:4]}-{x[4:6]}-{x[6:8]}" if len(x) == 8 and x.isascii() and x.isdigit() else ""


def ranks(value):
    """Return horse-number to corner rank; tied parentheses share a rank."""
    result, place = {}, 1
    for group in re.finditer(r"\(([^()]+)\)|(\d+)", normalize(value)):
        ids = re.findall(r"\d+", group[1]) if group[1] is not None else [group[2]]
        unique = []
        for item in ids:
            no = number(item)
            if no and no not in unique and no not in result:
                unique.append(no)
        for no in unique:
            result[no] = place
        place += len(unique)
    return result


def read_csv(data):
    for codec in ("utf-8-sig", "cp932"):
        try:
            return list(csv.reader(io.StringIO(data.decode(codec))))
        except UnicodeDecodeError:
            pass
    raise ValueError("Unknown NAR CSV encoding")


def rows_from_archive(path):
    p = Path(path)
    if p.is_dir():
        for file in p.glob("*.csv"):
            if file.stat().st_size < 75_000_000:
                yield file.name.lower(), read_csv(file.read_bytes())
    else:
        with zipfile.ZipFile(p) as archive:
            if len(archive.infolist()) > 25:
                raise ValueError("Unexpected NAR ZIP member count")
            for member in archive.infolist():
                if member.filename.lower().endswith(".csv") and member.file_size < 75_000_000:
                    yield Path(member.filename).name.lower(), read_csv(archive.read(member))


def item(row, offset):
    return str(row[offset]).strip() if len(row) > offset else ""


def race_key(row):
    return (normalize(item(row, 0)), date(item(row, 1)), number(item(row, 2)))


class NarOfficialArchive:
    def __init__(self, paths):
        race_rows, horse_rows = {}, []
        for path in paths:
            for filename, rows in rows_from_archive(path):
                if "racelist" in filename:
                    for row in rows:
                        key = race_key(row)
                        if key[1] and key[2]:
                            race_rows[key] = row
                if "horselist" in filename:
                    horse_rows.extend(row for row in rows if race_key(row)[1])
        self.race_count = len(race_rows)
        self.by_name = defaultdict(list)
        for h in horse_rows:
            race = race_rows.get(race_key(h))
            no = number(item(h, 5))
            name = normalize(item(h, 6))
            if not race or not no or not name:
                continue
            pairs = [(item(race, 50 + i), ranks(item(race, 58 + i))) for i in range(8)]
            pairs = [(label, ranks_) for label, ranks_ in pairs if label and ranks_]
            positions = [order.get(no) for _, order in pairs]
            if not any(p is not None for p in positions):
                continue
            laps = [float(item(race, i)) for i in range(35, 50) if item(race, i) and re.fullmatch(r"\d+(?:\.\d+)?", item(race, i))]
            run = {
                "date": date(item(h, 1)), "track": item(h, 0),
                "raceNumber": number(item(h, 2)), "distance": number(item(race, 23)),
                "horseNumber": no, "frameNumber": number(item(h, 3)),
                "fieldSize": number(item(race, 26)), "jockey": item(h, 14),
                "finish": number(item(h, 31)), "cornerNames": [x[0] for x in pairs],
                "cornerPositions": positions, "raceLapTimes": laps,
                "raceFirst3FSeconds": round(sum(laps[:3]), 2) if len(laps) >= 3 else None,
                "raceLapScope": "whole_race_not_individual_horse",
                "narOfficialCsv": True,
            }
            dob = date(item(h, 10))
            self.by_name[name].append((run, dob))
        for records in self.by_name.values():
            records.sort(key=lambda pair: pair[0]["date"], reverse=True)

    def horse_history(self, horse, race, limit=5):
        cutoff = date(race.get("date"))
        dob = date(horse.get("birthDate") or horse.get("birthday"))
        if not cutoff:
            return {}
        matched = [run.copy() for run, birth in self.by_name.get(normalize(horse.get("name")), [])
                   if run["date"] < cutoff and not (dob and birth and dob != birth)]
        return {"recentRaces": matched[:5], "allPastRuns": matched[:max(1, int(limit))]} if matched else {}


def register_nar_official_archive(registry: DataBankRegistry, paths=None):
    if paths is None:
        env = os.getenv("ARVEXQ_NAR_OFFICIAL_CSV_ARCHIVES", "")
        paths = env.split(os.pathsep) if env else []
    if not paths:
        return None
    archive = NarOfficialArchive(paths)
    registry.register(DataSource(
        name="nar_official_csv", circuit="NAR", priority=11,
        capabilities=SourceCapabilities(horse_history=True),
        fetchers={"horse_history": archive.horse_history},
    ))
    return archive
