"""Build bounded, observed race identities for independent real-odds transport."""
import base64
import gzip
import hashlib
import json
import re
from pathlib import Path
from scripts.arvexq_saved_odds import saved_odds


def _build_saved_sources(static: Path, dist: Path):
    directory = static / 'saved-snapshots'
    if not directory.is_dir():
        return
    target = dist / 'odds-sources'
    target.mkdir(exist_ok=True)
    for path in directory.glob('????-??-??.json'):
        manifest = json.loads(path.read_text())
        if manifest.get('version') != 'arvexq-saved-snapshots-v1':
            raise ValueError('invalid original manifest')
        races = {}
        backups = {}
        for rid, ref in manifest['races'].items():
            if ref['file'] != ref['sha256']+'.json':
                raise ValueError('invalid original path')
            envelope = json.loads((directory / ref['file']).read_text())
            raw = gzip.decompress(base64.b64decode(envelope['gzipBase64']))
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('original restore hash mismatch')
            d = json.loads(raw)
            if d.get('id') != rid or d.get('date') != manifest['date']:
                raise ValueError('original source identity mismatch')
            races[rid] = {k: d[k] for k in ('id','date','circuit','track','raceNumber','netkeibaRaceId') if k in d}
            races[rid]['sourceSnapshotSha256'] = ref['sha256']
            acquired = saved_odds(d, ref['sha256'])
            if acquired:backups[rid] = acquired
            races[rid]['horses'] = [{'horseNumber': h['horseNumber'], 'name': h['name']} for h in d['horses']]
        backup_target = dist / 'odds-backups'
        backup_target.mkdir(exist_ok=True)
        (backup_target / path.name).write_text(json.dumps({'version':'arvexq-saved-actual-odds-v1','date':manifest['date'],'races':backups},ensure_ascii=False,separators=(',', ':')),encoding='utf-8')
        (target / path.name).write_text(json.dumps({'version':'arvexq-odds-sources-v1',
            'date':manifest['date'],'races':races}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def _build_verified_racecard_sources(static: Path, dist: Path):
    """Add missing race identities from the independently verified static entry card.

    Saved-original identities take precedence. No market price or post-race
    outcome is reconstructed; only the roster needed to fetch official odds.
    """
    directory = static / "racecards"
    if not directory.is_dir():
        return
    target = dist / "odds-sources"
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(directory.glob("????-??-??.json")):
        raw = path.read_bytes()
        day = path.stem
        card = json.loads(raw)
        if (card.get("version") != "arvexq-static-entry-v1"
                or card.get("date") != day
                or not isinstance(card.get("races"), list)
                or card.get("raceCount") != len(card["races"])):
            raise ValueError("invalid verified static racecard " + path.name)
        output = target / path.name
        if output.exists():
            manifest = json.loads(output.read_text(encoding="utf-8"))
            if (manifest.get("version") != "arvexq-odds-sources-v1"
                    or manifest.get("date") != day
                    or not isinstance(manifest.get("races"), dict)):
                raise ValueError("invalid existing odds source manifest " + path.name)
            races = manifest["races"]
        else:
            manifest = {"version": "arvexq-odds-sources-v1", "date": day, "races": {}}
            races = manifest["races"]
        card_sha = hashlib.sha256(raw).hexdigest()
        observed = set()
        for row in card["races"]:
            if not isinstance(row, dict):
                raise ValueError("invalid verified racecard row")
            rid = row.get("id")
            match = re.fullmatch(r"(nar|jra)-(\d{4}-\d{2}-\d{2})-([^/?-]+)-(\d{2})", str(rid or ""))
            if (not match or match.group(2) != day
                    or match.group(3) != row.get("track")
                    or int(match.group(4)) != row.get("raceNumber")
                    or row.get("date") != day
                    or row.get("circuit") != ("地方" if match.group(1) == "nar" else "中央")
                    or rid in observed):
                raise ValueError("invalid verified race identity")
            observed.add(rid)
            horses = row.get("horses")
            if not isinstance(horses, list) or len(horses) < 2:
                raise ValueError("missing verified race runners")
            seen = set()
            minimal = []
            for horse in horses:
                if not isinstance(horse, dict):
                    raise ValueError("invalid verified runner")
                no = horse.get("horseNumber")
                name = horse.get("name")
                if (type(no) is not int or not (1 <= no <= 30)
                        or no in seen or not isinstance(name, str) or not name.strip()):
                    raise ValueError("invalid verified runner identity")
                seen.add(no)
                minimal.append({"horseNumber": no, "name": name})
            if rid in races:
                # The immutable saved original is authoritative for this identity.
                continue
            source = {
                "id": rid, "date": day, "circuit": row["circuit"],
                "track": row["track"], "raceNumber": row["raceNumber"],
                "horses": minimal, "sourceRacecardSha256": card_sha,
                "sourceRosterKind": "verified-static-racecard",
            }
            netkeiba_id = row.get("netkeibaRaceId")
            if isinstance(netkeiba_id, str) and re.fullmatch(r"\d{12}", netkeiba_id):
                source["netkeibaRaceId"] = netkeiba_id
            races[rid] = source
        output.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")


def build_sources(static: Path, dist: Path):
    """One manifest combining verified saved originals and static racecard IDs."""
    _build_saved_sources(static, dist)
    _build_verified_racecard_sources(static, dist)
