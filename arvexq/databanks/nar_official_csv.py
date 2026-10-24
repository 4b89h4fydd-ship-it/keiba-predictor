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
from datetime import datetime, timezone, timedelta

from .registry import DataBankRegistry, DataSource, SourceCapabilities


def normalize(value):
    return "".join(unicodedata.normalize("NFKC", str(value or "")).split())


def number(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def carried_weight(value):
    """Keep only an observed weight, including reduction-jockey prefixes."""
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def date(value):
    x = str(value or "").replace("-", "").replace("/", "")
    try:
        return datetime.strptime(x, "%Y%m%d").date().isoformat() if len(x) == 8 else ""
    except ValueError:
        return ""


def time_seconds(value):
    """Official mmssS timing, never a finishing-place or margin proxy."""
    text = str(value or "").strip()
    if not re.fullmatch(r"[0-9]{3,5}", text):
        return None
    seconds = int(text[-3:]) / 10
    if seconds >= 60:
        return None
    return (int(text[:-3]) * 60 if len(text) > 3 else 0) + seconds


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
        self.paths = tuple(str(path) for path in paths)
        race_rows, horse_rows = {}, []
        for path in self.paths:
            for filename, rows in rows_from_archive(path):
                if "racelist" in filename:
                    for row in rows:
                        key = race_key(row)
                        if key[1] and key[2]:
                            previous = race_rows.get(key)
                            if previous is None:
                                race_rows[key] = row
                            else:
                                richer, other = (row, previous) if sum(bool(str(v).strip()) for v in row) > sum(bool(str(v).strip()) for v in previous) else (previous, row)
                                race_rows[key] = [
                                    (richer[i] if i < len(richer) and str(richer[i]).strip()
                                     else other[i] if i < len(other) else "")
                                    for i in range(max(len(richer), len(other)))
                                ]
                if "horselist" in filename:
                    horse_rows.extend(row for row in rows if race_key(row)[1])
        self.race_count = len(race_rows)
        self.by_name = defaultdict(list)
        # Repeated daily/monthly records may differ in completeness.
        # Select the most populated observed row without inventing values.
        best_entries = {}
        for h in horse_rows:
            key = (race_key(h), number(item(h, 5)))
            if not key[0][1] or not key[1]:
                continue
            previous = best_entries.get(key)
            if previous is None:
                best_entries[key] = h
            else:
                if normalize(item(h, 6)) != normalize(item(previous, 6)) or (
                    date(item(h, 10)) and date(item(previous, 10))
                    and date(item(h, 10)) != date(item(previous, 10))
                ):
                    raise ValueError("conflicting horse identity in official archives")
                # Prefer the more complete observation for conflicting values,
                # then fill only blanks from the other official row.
                richer, other = (h, previous) if sum(bool(v.strip()) for v in h) > sum(bool(v.strip()) for v in previous) else (previous, h)
                width = max(len(richer), len(other))
                best_entries[key] = [
                    (richer[i] if i < len(richer) and str(richer[i]).strip()
                     else other[i] if i < len(other) else "")
                    for i in range(width)
                ]
        self.race_rows = race_rows
        self.entry_rows = best_entries
        winner_times = {}
        for h in best_entries.values():
            seconds = time_seconds(item(h, 32))
            if number(item(h, 31)) == 1 and seconds is not None:
                winner_times[race_key(h)] = seconds
        for h in best_entries.values():
            race = race_rows.get(race_key(h))
            no = number(item(h, 5))
            name = normalize(item(h, 6))
            if not race or not no or not name:
                continue
            pairs = [(item(race, 50 + i), ranks(item(race, 58 + i))) for i in range(8)]
            pairs = [(label, ranks_) for label, ranks_ in pairs if label and ranks_]
            positions = [order.get(no) for _, order in pairs]
            laps = [float(item(race, i)) for i in range(35, 50) if item(race, i) and re.fullmatch(r"\d+(?:\.\d+)?", item(race, i))]
            run = {
                "date": date(item(h, 1)), "track": item(h, 0),
                "raceNumber": number(item(h, 2)), "distance": number(item(race, 23)),
                "horseNumber": no, "frameNumber": number(item(h, 3)),
                "fieldSize": number(item(race, 26)), "jockey": item(h, 14),
                "surface": item(race, 21), "direction": item(race, 22),
                "weather": item(race, 24), "condition": item(race, 25),
                "class": item(race, 27),
                "carriedWeight": carried_weight(item(h, 16)),
                "trainer": item(h, 18), "birthDate": date(item(h, 10)),
                "sire": item(h, 11), "dam": item(h, 12), "damsire": item(h, 13),
                "timeSeconds": time_seconds(item(h, 32)),
                "circuit": "地方", "source": "NAR公式CSV",
                "raceId": f"nar-{date(item(h, 1))}-{item(h, 0)}-{number(item(h, 2)):02d}",
                "finish": number(item(h, 31)), "cornerNames": [x[0] for x in pairs],
                "cornerPositions": positions, "raceLapTimes": laps,
                "raceFirst3FSeconds": round(sum(laps[:3]), 2) if len(laps) >= 3 else None,
                "raceLapScope": "whole_race_not_individual_horse",
                "narOfficialCsv": True,
            }
            winner = winner_times.get(race_key(h))
            seconds = run["timeSeconds"]
            if run["finish"] > 0 and winner is not None and seconds is not None and seconds >= winner:
                run["marginSeconds"] = round(seconds - winner, 3)
                run["timeBehindWinner"] = run["marginSeconds"]
                run["marginEvidenceSource"] = "nar_official_csv"
                run["marginEvidence"] = {"winnerTimeSeconds": winner, "horseTimeSeconds": seconds}
            margin = item(h, 33)
            if margin and margin not in ("-", "--"):
                run["marginText"] = margin
            late = item(h, 34)
            if re.fullmatch(r"[0-9]{2}[.][0-9]", late):
                run["last3fSeconds"] = float(late)
            dob = date(item(h, 10))
            self.by_name[name].append((run, dob))
        for records in self.by_name.values():
            records.sort(key=lambda pair: pair[0]["date"], reverse=True)

    def horse_history(self, horse, race, limit=None):
        cutoff = date(race.get("date"))
        dob = date(horse.get("birthDate") or horse.get("birthday"))
        if not cutoff:
            return {}
        # Japanese racing ages increase on January 1: a 2026 three-year-old
        # must have been born in 2023, including when the source ran in 2025.
        age_match = re.search(r"\d+", str(horse.get("age") or ""))
        age = int(age_match.group()) if age_match else 0
        expected_birth_year = int(cutoff[:4]) - age if age > 0 else None
        if dob and expected_birth_year is not None and int(dob[:4]) != expected_birth_year:
            # Conflicting target identity fields cannot authorize any same-name join.
            return {}
        records = [(run, birth) for run, birth in self.by_name.get(normalize(horse.get("name")), [])
                   if run["date"] < cutoff]
        known_birthdates = {birth for _, birth in records if birth}
        if dob:
            valid_birthdates = {dob}
        elif expected_birth_year is not None:
            valid_birthdates = {birth for birth in known_birthdates
                                if int(birth[:4]) == expected_birth_year}
            if (known_birthdates and not valid_birthdates) or len(valid_birthdates) > 1:
                # Distinct same-name horses of the same racing age still need
                # the exact DOB; never arbitrarily select either one.
                return {}
        else:
            valid_birthdates = known_birthdates
            if len(valid_birthdates) > 1:
                # Without a birth date or racing age, the candidate is ambiguous.
                return {}
        conflicting_namesake = any(birth not in valid_birthdates for birth in known_birthdates)
        matched = [run.copy() for run, birth in records
                   if (not birth or birth in valid_birthdates)
                   and (birth or not conflicting_namesake)]
        # Missing-DOB archive rows cannot be assigned when a known conflicting
        # namesake exists. Otherwise preserve older historical observations.
        # The UI may request five rows, but full observed history is retained.
        return {"recentRaces": matched[:5], "allPastRuns": matched} if matched else {}


def register_nar_official_archive(registry: DataBankRegistry, paths=None):
    if paths is None:
        env = os.getenv("ARVEXQ_NAR_OFFICIAL_CSV_ARCHIVES", "")
        paths = env.split(os.pathsep) if env else []
    previous = registry.get("nar_official_csv")
    if previous:
        previous_fetch = previous.fetchers.get("horse_history")
        previous_archive = getattr(previous_fetch, "__self__", None)
        paths = list(dict.fromkeys([
            *(str(path) for path in (paths or [])),
            *(str(path) for path in getattr(previous_archive, "paths", ()) if Path(path).is_file()),
        ]))
    if not paths:
        return None
    archive = NarOfficialArchive(paths)
    registry.register(DataSource(
        name="nar_official_csv", circuit="NAR", priority=11,
        capabilities=SourceCapabilities(horse_history=True),
        fetchers={"horse_history": archive.horse_history},
    ))
    return archive


def preoff_three_way_odds(paths, race):
    """Decode user-supplied NAR *daily* odds ZIPs through the existing CSV lane.

    Official daily ZIP filename YYYYMMDD_<UNIX-timestamp>_odds.zip
    carries an observed-at timestamp. A monthly ZIP is final odds, never
    eligible as historical pre-off evidence. There is NO download here.
    A documented filename alone is not proof that a quote was actually
    published then; the caller must separately establish trusted provenance.
    """
    if race.get("circuit") not in ("地方", "nar", "NAR"):
        raise ValueError("NAR-only preoff odds")
    day = date(race.get("date"))
    track = normalize(race.get("track"))
    race_no = number(race.get("raceNumber") or race.get("raceNo"))
    post = str(race.get("scheduledStartTime") or race.get("startTime") or "").strip()
    times = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", post)
    if not times and re.fullmatch(r"\d{4}", post):
        times = re.fullmatch(r"(\d{2})(\d{2})", post)
    if not day or not track or not 1 <= race_no <= 12 or not times:
        raise ValueError("race identity and announced post time are required")
    hour, minute = map(int, times.groups())
    if hour > 23 or minute > 59:
        raise ValueError("invalid post time")
    jst = timezone(timedelta(hours=9))
    post_at = datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=jst)
    active_numbers = {number(h.get("horseNumber")) for h in race.get("horses") or []
                      if isinstance(h, dict) and not any(h.get(k) for k in ("scratched","cancelled","withdrawn"))}
    if len(active_numbers) < 3:
        raise ValueError("active starter numbers unavailable")
    latest = {}
    for raw_path in paths:
        path = Path(raw_path)
        match = re.fullmatch(r"(\d{8})_(\d{9,11})_odds[.]zip", path.name, re.IGNORECASE)
        if not match:
            # Monthly odds are only final odds. Never infer historical pre-off
            # timestamps from their filename or from a race finalization time.
            continue
        if date(match.group(1)) != day:
            continue
        observed = datetime.fromtimestamp(int(match.group(2)), tz=timezone.utc).astimezone(jst)
        if observed >= post_at or observed.date().isoformat() != day:
            continue
        for filename, rows in rows_from_archive(path):
            if not filename.endswith("_odds.csv"):
                continue
            for row in rows:
                if normalize(item(row, 0)) != track or date(item(row, 1)) != day:
                    continue
                if number(item(row, 2)) != race_no:
                    continue
                kind = normalize(item(row, 3))
                if kind not in ("3連単", "3連複"):
                    continue
                combo = tuple(number(item(row, i)) for i in (4, 5, 6))
                if any(n not in active_numbers for n in combo) or len(set(combo)) != 3:
                    continue
                # Horse order matters for trifecta; not for trio.
                if kind == "3連複":
                    combo = tuple(sorted(combo))
                try:
                    odd = float(item(row, 7))
                except ValueError:
                    continue
                if not 0 < odd < 1_000_000 or not __import__("math").isfinite(odd):
                    continue
                key = (kind, combo)
                prior = latest.get(key)
                if prior is None or prior["observedAt"] < observed.isoformat():
                    latest[key] = {"kind":kind, "horses":list(combo), "odds":odd,
                                   "observedAt":observed.isoformat(),
                                   "source":"NAR official daily odds ZIP",
                                   "archiveFile":path.name}
                elif prior["observedAt"] == observed.isoformat() and prior["odds"] != odd:
                    raise ValueError("conflicting official odds in identical timestamp")
    return [latest[key] for key in sorted(latest)]
