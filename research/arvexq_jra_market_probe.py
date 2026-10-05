#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
os.environ.setdefault('ARVEXQ_BOOTSTRAP_WARM','0')
os.environ.setdefault('ARVEXQ_DATA_CORE','0')
os.environ.setdefault('RACEDB_AUTO_UPDATE','0')
import app as prod
JST=timezone(timedelta(hours=9))

def fetch_html(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ja,en;q=0.8'})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read().decode('euc-jp','ignore')

def main():
    ds=(datetime.now(JST).date()-timedelta(days=1)).isoformat()
    rows=prod._netkeiba_race_summaries(ds) or []
    rows=[r for r in rows if str(r.get('id') or '').startswith('jra-')]
    print('DATE',ds,'SUMMARIES',len(rows))
    for summary in rows[:4]:
        rid=str(summary.get('id') or ''); nk=str(summary.get('netkeibaRaceId') or '')
        try: hs=prod._netkeiba_detail_rows(summary) or []
        except Exception as e:
            print('DETAIL_ERR',rid,repr(e)); continue
        print('RACE',rid,'NETKEIBA',nk,'HORSES',len(hs))
        print('PARSER_MARKET',json.dumps([{k:h.get(k) for k in ('horseNumber','name','winOdds','popularity')} for h in hs[:5]],ensure_ascii=False))
        if nk:
            url=f'https://race.netkeiba.com/race/result.html?race_id={nk}'
            try:
                soup=BeautifulSoup(fetch_html(url),'html.parser')
                table=soup.select_one('table.RaceTable01') or soup.find('table')
                trs=table.find_all('tr') if table else []
                print('RESULT_TABLE_ROWS',len(trs))
                for tr in trs[1:4]:
                    cells=[]
                    for td in tr.find_all(['td','th']):
                        cells.append({'text':' '.join(td.stripped_strings)[:80],'class':' '.join(td.get('class') or [])})
                    print('ROW_CELLS',json.dumps(cells,ensure_ascii=False))
            except Exception as e: print('HTML_ERR',repr(e))
        if hs: break
if __name__=='__main__':main()
