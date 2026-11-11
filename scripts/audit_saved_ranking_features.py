"""Audit a SHA-verified detail JSONL; never rebuild features from final horses.

Usage: PYTHONPATH=. python scripts/audit_saved_ranking_features.py details.jsonl output.jsonl
Input archive transport hashes must be verified by the collecting manifest reader.
"""
import sys
import json,collections
from pathlib import Path
from arvexq.prediction.mass_feature_transport import recover_mass_detail,_feature_hash
from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail
stats=collections.Counter();dates=collections.defaultdict(set);seen=set();runkeys=collections.Counter()
with open(sys.argv[2], 'w') as out:
 for line in open(sys.argv[1]):
  d=json.loads(line);rid=d['id']
  if '帯広' in rid:continue
  if rid in seen:stats['duplicate']+=1;continue
  seen.add(rid)
  try:r=recover_mass_detail(d)
  except ValueError:stats['invalid-archive']+=1;continue
  s=r.get('massFeatureSnapshot') or {}
  if s.get('featureHash')!=_feature_hash(s):stats['invalid-origin-hash']+=1;continue
  rows=frozen_training_rows_from_detail(r)
  if not rows:stats['no-settled-label']+=1;continue
  stats['usable-races']+=1;stats['horses']+=len(rows);dates[d.get('circuit')].add(d['date'])
  stats[d.get('circuit')]+=1
  for row in rows:out.write(json.dumps(row,ensure_ascii=False)+'\n')
print(json.dumps({'counts':stats,'dates':{c:sorted(v) for c,v in dates.items()}},ensure_ascii=False))
