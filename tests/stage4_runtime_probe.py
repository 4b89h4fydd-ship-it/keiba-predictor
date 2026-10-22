"""Run in each checkout with isolated empty databases; compare JSON outputs."""
import copy
import datetime
import inspect
import json
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import app

horse={'horseNumber':1,'name':'確認馬','recentRaces':[{'date':'2026-09-01','track':'大井','surface':'ダート','distance':1200,'finish':2,'fieldSize':12,'timeSeconds':73.2,'last3f':37.2,'passing':'3-3-2-2','bodyWeight':480}]}
race={'id':'nar-2026-10-18-大井-01','date':'2026-10-18','track':'大井','circuit':'地方','distance':1200,'surface':'ダート','horses':[horse],'result':{'status':'確定','finishers':[{'horseNumber':i,'finish':i} for i in [1,2,3]]}}
cases=[('normalize_central_race',({},)),('normalize_central_race',({'date':'2026-10-18','track':'東京','raceNumber':1,'horses':[horse]},)),('_jra_norm_cname',('pw01dde10%2FA',)),('_jra_track_from_cname',('invalid',)),('_jra_parse_past_cell',(BeautifulSoup('<td>未掲載</td>','html.parser').td,'2026-10-18')),('iter_months_back',(datetime.date(2026,1,1),3)),('_months_from_race_date',('2026-01-01',3)),('_history_counts',([], '2026-10-18')),('_pc_race_field',({},)),('_pc_finish_quality',({},)),('_pc_list_quality',([],1200)),('_pc_list_quality',(horse['recentRaces'],1200)),('_pc_style_metrics',(horse,race)),('_pc_sectional_score',(horse,race)),('_pc_fit_metrics',(horse,race)),('_is_jump_run',({'title':'障害未勝利'},)),('_is_jump_run',({'surface':'ダート'},)),('_restore_saved_odds',({'horses':[{'horseNumber':1,'winOdds':3.2}]} ,)),('_result_has_podium',(race,)),('_result_has_podium',({},)),('_bootstrap_display_ready',(race,)),('_bootstrap_display_ready',(None,)),('_snapshot_final',(race,)),('_v215_speed_ratio',(horse['recentRaces'][0],)),('_pc_live_track_speed',(race,)),('_strip_excluded',({'horses':[{'horseNumber':1},{'horseNumber':2,'scratched':True}]},)),('_race_volatility',(race,)),('_parse_payouts',(BeautifulSoup('<table><tr><th>単勝</th><td>1</td><td>250円</td><td>1</td></tr></table>','html.parser'),)),('_parse_nar_live_odds_html',('<table><tr><th>馬番</th><th>単勝</th></tr><tr><td>1</td><td>3.2</td></tr></table>',)),('_parse_nar_official_card_html',(race,'<html>未掲載</html>')),('_merge_card_rows_preserve',(race,[{'horseNumber':1,'winOdds':3.2}])),('_merge_fast_history',(race,[{'horseNumber':1,'name':'確認馬','recentRaces':[{'date':'2026-09-01','finish':2}]}]))]
results=[]
for name,args in cases:
 args=copy.deepcopy(args)
 value=getattr(app,name)(*args)
 if inspect.isgenerator(value):value=list(value)
 results.append({'name':name,'output':value,'input_after':args})
client=TestClient(app.app)
responses=[]
for path in ['/version.json','/','/manifest-arvexq-v175.webmanifest','/api/v1/central-schema','/api/v1/enrichment-schema']:
 r=client.get(path);assert r.status_code==200,(path,r.status_code);responses.append({'path':path,'status':r.status_code,'body':r.text,'content_type':r.headers.get('content-type')})
print(json.dumps({'functions':results,'http':responses,'openapi':app.app.openapi()},ensure_ascii=False,sort_keys=True,default=str))
