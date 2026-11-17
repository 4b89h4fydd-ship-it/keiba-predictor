"""Immutable research identity ledger. Run locally or as a MotherDuck Flight.

Does not assert full race coverage from a partial horse history. Ambiguous
identities and conflicting values remain observations, never merged facts.
"""
import collections
import datetime
import hashlib
import json
import re
import tempfile
import unicodedata

VERSION = 'identity-ledger-v1'
DEST = 'arvexq_history_research.main'


def compact(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(v):
    return hashlib.sha256(compact(v).encode()).hexdigest()


def text(v):
    return unicodedata.normalize('NFKC', str(v or '')).strip()


def normalize(horse, name, raw):
    p = json.loads(raw) if isinstance(raw, str) else raw
    reasons = []
    day = text(p.get('date') or p.get('raceDate'))
    try:
        day = datetime.date.fromisoformat(day).isoformat()
    except ValueError:
        day = None
        reasons.append('invalid_or_missing_date')
    track = text(p.get('track'))
    # Only explicit suffix normalization; no fuzzy matching of venues/names.
    if track.endswith('競馬場'):
        track = track[:-3]
    n = p.get('raceNumber')
    try:
        n = int(n) if float(n).is_integer() and 1 <= float(n) <= 99 else None
    except (ValueError, TypeError, OverflowError):
        n = None
    rid = text(p.get('raceId'))
    matched = re.fullmatch(r'(jra|nar)-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})', rid)
    if matched and (day != matched[2] or track != matched[3] or (n is not None and n != int(matched[4]))):
        reasons.append('race_id_metadata_conflict')
    # Circuit is not guessed from a title. Explicit source race IDs can supply it.
    circuit = matched[1] if matched else None
    if not track:
        reasons.append('missing_track')
    if n is None:
        reasons.append('missing_race_number')
    if not circuit:
        reasons.append('unverified_race_id_namespace')
    hid = text(horse)
    if not hid or hid.startswith('name:'):
        reasons.append('missing_stable_horse_id')
        hid = None
    race_key = digest([circuit, day, track, n]) if not reasons else None
    fields = {k: p.get(k) for k in ('title', 'distance', 'surface', 'finish', 'timeSeconds',
              'marginSeconds', 'marginText', 'last3f', 'cornerPositions', 'jockey',
              'carriedWeight', 'fieldSize', 'condition')}
    fields.update(horse_id=hid, horse_name=text(name), day=day, track=track,
                  race_number=n, source_race_id=rid or None,
                  acquired_at=p.get('acquiredAt') or p.get('fetchedAt'),
                  data_source=p.get('source') or p.get('dataSource'),
                  race_key=race_key, entry_key=digest([race_key,hid]) if race_key else None,
                  reasons=reasons, raw=p)
    return fields


def roster(snap):
    horses = snap.get('horses') or []
    fins = (snap.get('result') or {}).get('finishers') or []
    issues = []
    active = []
    for h in horses:
        if not isinstance(h, dict):
            issues.append('invalid_entry'); continue
        if h.get('scratched') is True or h.get('withdrawn') is True or h.get('status') in ('取消','除外'):
            continue
        active.append(h.get('horseNumber'))
    nums = [f.get('horseNumber') for f in fins if isinstance(f, dict)]
    if None in active or None in nums:
        issues.append('missing_horse_number')
    if len(set(active)) != len(active) or len(set(nums)) != len(nums):
        issues.append('duplicate_horse_number')
    if set(active) != set(nums):
        issues.append('roster_mismatch')
    positions = []
    for f in fins:
        v = f.get('finish') if isinstance(f,dict) else None
        if isinstance(v, (float,int)) and not isinstance(v,bool) and v > 0 and int(v)==v:
            positions.append(int(v))
        else:
            issues.append('unresolved_nonfinish_status')
    # Competition ranking allows 1,1,3 and 1,2,2,4 without rewriting labels.
    valid = bool(positions) and all(pos == 1 + sum(q < pos for q in positions) for pos in positions)
    if not valid:
        issues.append('invalid_competition_ranks')
    return sorted(set(issues)), len(set(positions)) < len(positions)


def main():
    import duckdb
    c = duckdb.connect('md:')
    c.execute("SET TimeZone='UTC'")
    before = c.execute('SELECT count(*), bit_xor(hash(race_id,sha256)) FROM my_db.arvexq_analytics.race_snapshots').fetchone()
    raw = c.execute('SELECT source_race_id,horse_key,horse_name,history_source,run_hash,CAST(payload AS VARCHAR) FROM arvexq_history_research.main.past_run_observations ORDER BY source_race_id,horse_key,history_source,run_hash').fetchall()
    dataset = digest([VERSION, before, raw])
    groups = collections.defaultdict(list)
    observations = []
    for source,horse,name,kind,rhash,p in raw:
        v = normalize(horse,name,p)
        obs = dict(dataset_id=dataset, observation_id=digest([source,horse,kind,rhash,p]),
                   source_snapshot=source, history_source=kind, run_hash=rhash, normalized=v)
        observations.append(obs)
        if v['entry_key']:
            groups[v['entry_key']].append(v)
    entries = []
    for key, vals in groups.items():
        variants = {digest({k:v for k,v in x.items() if k not in ('raw','horse_name','acquired_at','data_source','reasons')} ) for x in vals}
        entries.append(dict(dataset_id=dataset,entry_key=key,race_key=vals[0]['race_key'],horse_id=vals[0]['horse_id'],
                            observation_count=len(vals), variant_count=len(variants),
                            status='conflicting_values' if len(variants)>1 else 'identity_linked'))
    audits=[]
    for rid,sha,day,s in c.execute('SELECT race_id,sha256,CAST(race_date AS VARCHAR),CAST(snapshot_json AS VARCHAR) FROM my_db.arvexq_analytics.race_snapshots ORDER BY race_id').fetchall():
        snap=json.loads(s)
        issues,tied=roster(snap)
        settled=(snap.get('result') or {}).get('status')=='確定'
        bucket='F' if '帯広' in rid or snap.get('track')=='帯広' else 'D' if not settled else 'E' if issues else 'C'
        audits.append(dict(dataset_id=dataset,race_id=rid,source_sha=sha,day=day,bucket=bucket,
                           issues=issues,tied=tied,disposition='exclude_pending_evidence' if bucket=='E' else 'research_only',
                           reason='preoff_availability_not_certified',
                           debut='新馬' in str(snap.get('title') or snap.get('name') or ''),
                           obstacle='障害' in str(snap.get('surface') or snap.get('title') or '')))
    summary=dict(dataset_id=dataset,version=VERSION,snapshots=before[0],observations=len(raw),
                 legacy_json_unique=len({(h,r) for _,h,_,_,r,_ in raw}),
                 linked_observations=sum(len(v) for v in groups.values()),
                 identity_entries=len(entries),independent_race_identities=len({e['race_key'] for e in entries}),
                 repeated_identity_observations=sum(len(v)-1 for v in groups.values()),
                 conflicting_entries=sum(e['variant_count']>1 for e in entries),
                 unresolved_observations=sum(not o['normalized']['entry_key'] for o in observations),
                 reasons=dict(collections.Counter(r for o in observations for r in o['normalized']['reasons'])),
                 buckets=dict(collections.Counter(a['bucket'] for a in audits)),
                 issues=dict(collections.Counter(i for a in audits for i in a['issues'])),
                 tied_races=sum(a['tied'] for a in audits),newly_acquired_races=0,
                 warning='Partial histories are not complete race rosters. C is not A. No new sealed holdout.')
    assert summary['linked_observations']+summary['unresolved_observations']==len(raw)
    c.execute('BEGIN')
    try:
        for table, values in [('history_identity_observations_v1',observations),('history_identity_entries_v1',entries),('history_race_audit_v1',audits),('history_identity_runs_v1',[summary])]:
            with tempfile.NamedTemporaryFile(mode='w',suffix='.jsonl') as f:
                for v in values:
                    flat={k:compact(x) if isinstance(x,(dict,list)) else x for k,x in v.items()}
                    f.write(compact(flat)+'\n')
                f.flush()
                c.execute(f"CREATE TABLE IF NOT EXISTS {DEST}.{table} AS SELECT * FROM read_json_auto(?,format='newline_delimited',maximum_depth=-1) WHERE false",[f.name])
                exists=c.execute(f'SELECT count(*) FROM {DEST}.{table} WHERE dataset_id=?',[dataset]).fetchone()[0]
                if not exists:
                    c.execute(f"INSERT INTO {DEST}.{table} BY NAME SELECT * FROM read_json_auto(?,format='newline_delimited',maximum_depth=-1)",[f.name])
                assert c.execute(f'SELECT count(*) FROM {DEST}.{table} WHERE dataset_id=?',[dataset]).fetchone()[0]==len(values)
        assert c.execute('SELECT count(*), bit_xor(hash(race_id,sha256)) FROM my_db.arvexq_analytics.race_snapshots').fetchone()==before
        c.execute('COMMIT')
    except Exception:
        c.execute('ROLLBACK'); raise
    print('VERIFIED',compact(summary),flush=True)

if __name__=='__main__': main()
