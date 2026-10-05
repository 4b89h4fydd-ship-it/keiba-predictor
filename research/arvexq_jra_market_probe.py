#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
os.environ.setdefault('ARVEXQ_BOOTSTRAP_WARM','0')
os.environ.setdefault('ARVEXQ_DATA_CORE','0')
os.environ.setdefault('RACEDB_AUTO_UPDATE','0')
import app as prod
JST=timezone(timedelta(hours=9))

def main():
    ds=(datetime.now(JST).date()-timedelta(days=1)).isoformat()
    rows=prod._netkeiba_race_summaries(ds) or []
    rows=[r for r in rows if str(r.get('id') or '').startswith('jra-')]
    print('DATE',ds,'SUMMARIES',len(rows))
    for summary in rows[:4]:
        rid=str(summary.get('id') or '')
        try: hs=prod._netkeiba_detail_rows(summary) or []
        except Exception as e:
            print('DETAIL_ERR',rid,repr(e)); continue
        try: rr=prod._netkeiba_current_result(summary) or {}
        except Exception as e:
            rr={}; print('RESULT_ERR',rid,repr(e))
        print('RACE',rid,'HORSES',len(hs),'SUMMARY_KEYS',sorted(summary.keys()))
        print('HORSE_SAMPLE',json.dumps([{k:h.get(k) for k in sorted(h.keys()) if k in ('horseNumber','name','winOdds','popularity','odds','oddsSource','bodyWeight','bodyWeightChange')} for h in hs[:5]],ensure_ascii=False))
        fins=(rr.get('finishers') or [])[:5]
        print('FINISH_SAMPLE',json.dumps([{k:f.get(k) for k in sorted(f.keys()) if k.lower() in ('horsenumber','finish','winodds','popularity','odds')} for f in fins],ensure_ascii=False))
        if hs: print('HORSE_KEYS',sorted(hs[0].keys()))
        print('RESULT_KEYS',sorted(rr.keys()) if isinstance(rr,dict) else type(rr).__name__)
        if hs: break
if __name__=='__main__':main()
