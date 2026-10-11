"""Baseline replay and independent storage/collector verification for Stage 5."""
import ast
import copy
import gzip
import hashlib
import importlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app
import pytest
from fastapi.testclient import TestClient
from test_acquisition_integration import central_row

ROOT = Path(__file__).resolve().parents[1]
METHODS = json.loads((ROOT / 'docs/refactor/stage5-methods.json').read_text())
FUNCTIONS = json.loads((ROOT / 'docs/refactor/stage5-functions.json').read_text())
STORE_SOURCE = gzip.decompress((ROOT / 'tests/fixtures/storage-19b76d3.py.gz').read_bytes()).decode()
FUNCTION_SOURCE = gzip.decompress((ROOT / 'tests/fixtures/storage-coordinators-19b76d3.py.gz').read_bytes()).decode()


def legacy():
    namespace = dict(vars(app))
    exec(compile(STORE_SOURCE, 'storage-19b76d3.py', 'exec'), namespace)
    return namespace


class UndoPorts(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) \
                and node.value.value.id == 'self' and node.value.attr == '_ports':
            return ast.copy_location(ast.Name(node.attr, node.ctx), node)
        if isinstance(node.value, ast.Name) and node.value.id == '_state':
            return ast.copy_location(ast.Name(node.attr, node.ctx), node)
        return self.generic_visit(node)


@pytest.mark.parametrize('record', METHODS, ids=lambda r: r['class']+'.'+r['method'])
def test_method_body_sql_and_interfaces_match_original(record):
    original_tree = ast.parse(STORE_SOURCE)
    original_class = next(n for n in original_tree.body if isinstance(n, ast.ClassDef) and n.name == record['class'])
    original = next(n for n in original_class.body if isinstance(n, ast.FunctionDef) and n.name == record['method'])
    assert hashlib.sha256(ast.dump(original, include_attributes=False).encode()).hexdigest() == record['ast_sha256']
    source=(ROOT / record['after']).read_text()
    hooks={
        'NarStore': '            begin_write(self.conn)\n            races, entries = retain_archive_rows(self.conn, races, list(entries))\n            race_lookup = {(r.track, r.date, r.race_no): r for r in races}\n',
        'CentralStore': '                    incoming=retain_snapshot(old,incoming)\n',
        'PreparedRaceStore': '                retained=retain_snapshot(previous,detail)\n                detail.clear();detail.update(retained)\n                payload=json.dumps(detail,ensure_ascii=False,separators=(",",":"))\n',
        'RaceDataBank': '                detail=retain_snapshot(previous,detail)\n',
    }
    if record['method'] in {'import_rows','upsert','put','upsert_race'} and record['class'] in hooks:
        hook=hooks[record['class']]
        assert source.count(hook)==1
        source=source.replace(hook,'')
        if record['class']=='NarStore':
            source=source.replace('        races = list(races)\n','        races = list(races)\n        race_lookup = {(r.track, r.date, r.race_no): r for r in races}\n')
    if record['class']=='CentralStore' and record['method']=='upsert':
        source=source.replace('            begin_write(self.conn)\n','')
    if record['class']=='RaceDataBank' and record['method']=='upsert_race':
        source=source.replace('            begin_write(conn)\n','')
    if record['class']=='DayBundleStore' and record['method']=='put':
        source=source.replace('            if not accept_bundle(conn,race_date,payload,complete):return\n','')
    market_hooks={'save_odds':'        rows=retain_odds(self.path,race_id,rows)\n',
                  'save_analysis':'        payload=retain_analysis(self.path,race_id,payload)\n'}
    if record['method'] in market_hooks:
        hook=market_hooks[record['method']]
        assert source.count(hook)==1
        source=source.replace(hook,'')
    target = ast.parse(source)
    owner = next(n for n in target.body if isinstance(n, ast.ClassDef) and n.name == record['owner'])
    moved = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == record['method'])
    moved = UndoPorts().visit(moved)
    if record['method'] == '__init__' and record['class'] in {'PreparedRaceStore','RaceDataBank'}:
        moved.args.kwonlyargs = original.args.kwonlyargs
        moved.args.kw_defaults = original.args.kw_defaults
        moved.body.pop(0)  # Explicit ports are the sole constructor addition.
    assert ast.dump(moved, include_attributes=False) == ast.dump(original, include_attributes=False)


@pytest.mark.parametrize('record', FUNCTIONS, ids=lambda r: r['name'])
def test_coordinator_body_and_control_flow_match_original(record):
    original = next(n for n in ast.parse(FUNCTION_SOURCE).body if n.name == record['name'])
    assert hashlib.sha256(ast.dump(original, include_attributes=False).encode()).hexdigest() == record['ast_sha256']
    target = ast.parse((ROOT / record['after']).read_text())
    moved = next(n for n in target.body if isinstance(n, ast.FunctionDef) and n.name == record['name'])
    moved = UndoPorts().visit(moved)
    moved.args.kwonlyargs = original.args.kwonlyargs
    moved.args.kw_defaults = original.args.kw_defaults
    original.body = [n for n in original.body if not isinstance(n, ast.Global)]
    assert ast.dump(moved, include_attributes=False) == ast.dump(original, include_attributes=False)


def dump_db(path):
    with sqlite3.connect(path) as conn:
        return '\n'.join(conn.iterdump())


@pytest.mark.parametrize('store_name', ['NarStore','CentralStore','PreparedRaceStore','RaceDataBank','DayBundleStore'])
def test_sqlite_schema_payload_updates_and_reopen_exact_baseline(tmp_path, store_name):
    outputs=[]; databases=[]
    for label, cls in [('old',legacy()[store_name]),('new',getattr(app,store_name))]:
        path=tmp_path/(label+'.sqlite3')
        with patch('time.time', return_value=1_800_000_000):
            store=cls(path)
            detail=central_row()
            rid=detail['id']
            if store_name == 'NarStore':
                race=app.RaceRow('大井','2026-10-10',1,'15:00','試験',1200,'晴','良',1,(100,40,20,10,5),[{1:1}])
                entry=app.EntryRow('大井','2026-10-10',1,1,1,'地方試験馬','牡',3,56.0,'騎手','調教師',1,73.0)
                store.import_rows([race],[entry]);store.import_rows([race],[entry])
                store.mark_synced('daily',Path('/fixture/archive.zip'))
                outputs.append([store.races_json(race.date),store.stats("jockey",entry.jockey,"2026-10-11"),store.coverage(),store.synced_at('daily'),
                                store.recent_races(entry.name,'2026-10-11',100),store.prize_before(entry.name,'2026-10-11')])
            elif store_name == 'CentralStore':
                store.upsert([detail]);store.upsert([{'id':rid,'date':detail['date'],'track':'東京','raceNumber':1,'horses':[]}])
                outputs.append([store.races_json(detail['date']),store.coverage()])
            elif store_name == 'PreparedRaceStore':
                store.put(detail);store.put({'id':rid,'horses':[]})
                outputs.append(store.get(rid))
            elif store_name == 'RaceDataBank':
                store.upsert_race(detail)
                store.upsert_past_runs(detail['horses'][0],detail['horses'][0]['allPastRuns'])
                store.upsert_past_runs(detail['horses'][0],detail['horses'][0]['recentRaces'])
                store.save_odds(rid,[{'horseNumber':1,'winOdds':3.5,'popularity':2}], 'fixture')
                store.save_odds(rid,[])
                store.save_analysis(rid,{'horses':detail['horses'],'scenarios':{'A':1}})
                store.mark_source('fixture','done','ok')
                outputs.append([store.get_race(rid),store.odds_latest(rid),store.get_analysis(rid),store.source_updated('fixture')])
                with sqlite3.connect(path) as conn:
                    assert conn.execute('SELECT count(*) FROM past_runs').fetchone()[0] == 12
            else:
                store.put(detail['date'],{'raceCount':1,'detailCount':1,'details':[detail]},True)
                outputs.append(store.get(detail['date'],True))
            if hasattr(store,'conn'):store.conn.close()
            # Existing files are reopened, not rebuilt, by the new schema owner.
            again=getattr(app,store_name)(path)
            if hasattr(again,'conn'):again.conn.close()
        databases.append(dump_db(path))
    assert outputs[0] == outputs[1]
    assert databases[0] == databases[1]


def test_new_modules_import_without_app_io_or_threads():
    modules=sorted({r['after'][:-3].replace('/','.') for r in METHODS+FUNCTIONS} |
                   {str(p.relative_to(ROOT))[:-3].replace('/','.') for p in (ROOT/'arvexq/storage').rglob('*.py')})
    code=('import importlib,sqlite3,threading,urllib.request,sys\n'
          'def fail(*a,**k): raise AssertionError("import side effect")\n'
          'sqlite3.connect=fail\nthreading.Thread.start=fail\nurllib.request.urlopen=fail\n'
          f'for name in {modules!r}: importlib.import_module(name)\n'
          'assert "app" not in sys.modules\n')
    subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,timeout=20)
    for module in modules:
        path=ROOT/(module.replace('.','/')+'.py')
        assert len(path.read_text().splitlines()) < 500
        assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'exec','eval','globals'}
                       for n in ast.walk(ast.parse(path.read_text())))


def test_feature_locks_and_states_are_independent():
    owners=['history','live','commercial','environment','data_core','prewarm','fast_card','odds','bootstrap','racedb']
    seen=[]
    for name in owners:
        module=importlib.import_module('arvexq.infra.collectors.'+name+'_state')
        locks=[v for k,v in vars(module).items() if k.endswith(('_lock','_cv'))]
        assert locks
        for lock in locks:
            assert all(lock is not previous for previous in seen)
            seen.append(lock)


def test_fast_card_failure_releases_only_its_running_slot():
    from arvexq.infra.collectors.fast_card import _fast_card_worker
    class StopWorker(BaseException):pass
    class QueueCondition:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def wait(self):raise StopWorker()
    running=set();pending={'fixture'};queue=[(10,100,'fixture')]
    with pytest.raises(StopWorker):
        _fast_card_worker(_fast_card_cv=QueueCondition(),_fast_card_pending=pending,_fast_card_queue=queue,
                          _fast_card_running=running,_hydrate_fast_card_now=lambda *a,**k: (_ for _ in ()).throw(TimeoutError()),
                          _build_fast_diagnosis_snapshot=lambda *a,**k: pytest.fail('failed hydrate'))
    assert not running and not pending and not queue


def test_data_core_failure_does_not_poison_other_collectors():
    from arvexq.infra.collectors.data_core import _data_core_cycle
    record=next(r for r in FUNCTIONS if r['name']=='_data_core_cycle')
    ports={name:getattr(app,name) for name in record['dependencies'] if name!='_state'}
    state={'running':False};ports['_data_core_state']=state
    ports['_data_core_day_rows']=lambda *a: (_ for _ in ()).throw(TimeoutError('fixture'))
    before=copy.deepcopy(app._auto_odds_state)
    _data_core_cycle(**ports)
    assert state['running'] is False and state['error']=='fixture'
    assert app._auto_odds_state == before


def test_real_stores_to_api_preserve_career_and_market_contract(tmp_path):
    bank=app.RaceDataBank(tmp_path/'racedb.sqlite3');prepared=app.PreparedRaceStore(tmp_path/'prepared.sqlite3')
    detail=central_row();rid=detail['id']
    bank.upsert_race(detail);prepared.put(copy.deepcopy(detail))
    bank.save_odds(rid,[{'horseNumber':1,'winOdds':4.2,'popularity':3}],'fixture')
    bank.save_analysis(rid,{'id':rid,'scenarios':{},'horses':detail['horses']})
    with patch.object(app,'RACEDB',bank),patch.object(app,'PREPARED_STORE',prepared):
        client=TestClient(app.app)
        response=client.get('/api/v1/racedb-race/'+rid)
        assert response.status_code==200
        analysis=client.get('/api/v1/racedb/analysis/'+rid)
        assert analysis.status_code==200
        assert len(analysis.json()['analysis']['horses'][0]['allPastRuns'])==12


@pytest.mark.parametrize('store_name',['CentralStore','PreparedRaceStore','RaceDataBank'])
def test_partial_update_retains_healthy_card_result_and_recorded_ticket(tmp_path,store_name):
    store=getattr(app,store_name)(tmp_path/'retention.sqlite3')
    detail=central_row();detail['result']={'status':'確定','finishers':[{'horseNumber':1,'finish':1}],
                                        'payouts':[{'type':'単勝','amount':350}]}
    detail['preRaceBet']={'fixedAt':'2026-10-10T14:55:00+09:00','items':[{'nums':[1,2]}]}
    detail['morningMarkSnapshot']={'generatedAt':'morning','marks':{'1':'◎'}}
    if store_name=='CentralStore':
        write=lambda value:store.upsert([value]);read=lambda:store.races_json(detail['date'])[0]
    elif store_name=='PreparedRaceStore':
        write=lambda value:store.put(value,force=True);read=lambda:store.get(detail['id'])[0]
    else:
        write=store.upsert_race;read=lambda:store.get_race(detail['id'])[0]
    write(copy.deepcopy(detail))
    before=copy.deepcopy(read())
    partial={'id':detail['id'],'date':detail['date'],'track':'東京','raceNumber':1,
             'circuit':'中央','horses':[{'horseNumber':1,'name':'中央試験馬','recentRaces':[]}],
             'weather':'不明','condition':'','result':{},
             'preRaceBet':{'items':[{'nums':[9]}]},'morningMarkSnapshot':{'marks':{'1':'×'}}}
    write(partial);after=read()
    for key in ('result','preRaceBet','morningMarkSnapshot','weather','condition','distance'):
        assert after[key]==before[key]
    assert after['horses'][0]['recentRaces']==before['horses'][0]['recentRaces']
    if hasattr(store,'conn'):store.conn.close()


@pytest.mark.parametrize('store_name',['PreparedRaceStore','RaceDataBank'])
def test_forced_post_off_update_cannot_change_sealed_prediction_or_bets(tmp_path,store_name):
    from datetime import datetime,timedelta
    from arvexq.prediction.prerace_archive import JST,seal_detail
    from test_prerace_archive import race,forecast
    now=datetime(2026,10,8,19,50,tzinfo=JST)
    detail=seal_detail(race(now),forecast(race(now),now),now)
    detail['preRaceBet']={'fixedAt':now.isoformat(),'items':[{'nums':[1,2,3]}]}
    store=getattr(app,store_name)(tmp_path/'frozen.sqlite3')
    write=(lambda value:store.put(value,force=True)) if store_name=='PreparedRaceStore' else store.upsert_race
    write(copy.deepcopy(detail))
    first=store.get(detail['id'])[0] if store_name=='PreparedRaceStore' else store.get_race(detail['id'])[0]
    incoming=copy.deepcopy(detail)
    incoming['preRacePrediction']=forecast(incoming,now+timedelta(hours=1))
    incoming['preRaceBet']={'items':[{'nums':[9]}]}
    incoming['result']={'status':'確定','finishers':[{'horseNumber':3,'finish':1}]}
    write(incoming);saved=store.get(detail['id'])[0] if store_name=='PreparedRaceStore' else store.get_race(detail['id'])[0]
    assert saved['preRacePrediction']==first['preRacePrediction']
    assert saved['preRaceBet']==detail['preRaceBet']
    assert saved['result']['finishers'][0]['horseNumber']==3


def test_nar_partial_csv_keeps_results_and_scheduled_start(tmp_path):
    from dataclasses import replace
    store=app.NarStore(tmp_path/'nar.sqlite3')
    race=app.RaceRow('大井','2026-10-10',1,'15:00','試験',1200,'晴','良',1,(100,40,20,10,5),[{1:1}])
    entry=app.EntryRow('大井','2026-10-10',1,1,1,'試験馬','牡',3,56.0,'騎手','調教師',1,73.0)
    store.import_rows([race],[entry])
    store.import_rows([replace(race,start_time='15:05',title='',distance=0,field_size=0,weather='不明',condition='',
                               prize=(0,0,0,0,0),corners=[])],
                      [replace(entry,frame_no=0,name='',age=0,carried_weight=0,jockey='',trainer='',finish=0,time_seconds=0)])
    saved=store.conn.execute('SELECT * FROM races').fetchone();horse=store.conn.execute('SELECT * FROM entries').fetchone()
    assert saved['start_time']=='15:05' and saved['scheduled_start_time']=='15:00'
    assert (saved['distance'],saved['weather'],saved['condition'],saved['prize1'])==(1200,'晴','良',100)
    assert (horse['name'],horse['finish'],horse['time_seconds'],horse['corner_positions_json'])==('試験馬',1,73.0,'[1]')
    store.conn.close()


def test_full_career_union_never_changes_recent_five_or_meaningful_zero():
    from arvexq.storage.policies.snapshots import retain_snapshot
    old=central_row();new=copy.deepcopy(old)
    new['horses'][0]['allPastRuns']=new['horses'][0]['allPastRuns'][:5]
    new['horses'][0]['bodyWeightChange']=0
    old['horses'][0]['bodyWeightChange']=4
    merged=retain_snapshot(old,new)
    assert len(merged['horses'][0]['allPastRuns'])==12
    assert len(merged['horses'][0]['recentRaces'])==5
    assert merged['horses'][0]['bodyWeightChange']==0
    assert len(new['horses'][0]['allPastRuns'])==5


def test_nonempty_card_does_not_reintroduce_withdrawn_horse():
    from arvexq.storage.policies.snapshots import retain_snapshot
    old=central_row();old['horses'].append({'horseNumber':2,'name':'取消馬'})
    update=central_row();merged=retain_snapshot(old,update)
    assert [h['horseNumber'] for h in merged['horses']]==[1]


@pytest.mark.parametrize('enabled',['0','1'])
@pytest.mark.parametrize('name',['_start_commercial_collector','_start_environment_collector',
                                 '_start_data_core_collector','_start_auto_odds_collector',
                                 '_start_site_bootstrap_warmer','_start_racedb_daemon'])
def test_collector_start_gates_and_thread_contract_match_baseline(name,enabled):
    import threading
    calls=[];outputs=[]
    class Thread:
        def __init__(self,target,daemon=False,name=None,**kwargs):
            calls.append(('thread',target.__name__,daemon,name))
        def start(self):calls.append(('start',))
    for mode in ('old','new'):
        calls.clear()
        ns=dict(vars(app));ns.update(_racedb_daemon_started=False)
        exec(compile(FUNCTION_SOURCE,'coordinators-19b76d3.py','exec'),ns)
        env={key:enabled for key in ('ARVEXQ_COMMERCIAL_COLLECTOR','ARVEXQ_ENVIRONMENT_COLLECTOR',
             'ARVEXQ_DATA_CORE','ARVEXQ_AUTO_ODDS','ARVEXQ_BOOTSTRAP_WARM','RACEDB_AUTO_UPDATE')}
        if name=='_start_racedb_daemon':env['ARVEXQ_COMMERCIAL_COLLECTOR']='0'
        with patch.dict('os.environ',env),patch.object(threading,'Thread',Thread):
            if mode=='old':ns[name]()
            else:
                record=next(r for r in FUNCTIONS if r['name']==name)
                ports={key:getattr(app,key) for key in record['dependencies'] if key!='_state'}
                if '_state' in record['dependencies']:ports['_state']=SimpleNamespace(_racedb_daemon_started=False)
                module=importlib.import_module(record['after'][:-3].replace('/','.'))
                getattr(module,name)(**ports)
        outputs.append(copy.deepcopy(calls))
    assert outputs[0]==outputs[1]


def test_partial_analysis_and_odds_updates_keep_healthy_data(tmp_path):
    store=app.RaceDataBank(tmp_path/'market.sqlite3');rid='fixture'
    store.save_odds(rid,[{'horseNumber':1,'winOdds':3.5,'popularity':2}],'fixture',captured_at=120)
    store.save_odds(rid,[{'horseNumber':1,'winOdds':None,'popularity':3}],'fixture',captured_at=150)
    assert store.odds_latest(rid)[0]['winOdds']==3.5
    assert store.odds_latest(rid)[0]['popularity']==3
    analysis={'scenarios':{'A':{'pace':45}},'horses':[{'horseNumber':1,'name':'馬','allPastRuns':[{'date':'2026-01-01'}]}]}
    store.save_analysis(rid,analysis);store.save_analysis(rid,{'scenarios':{},'horses':[]})
    assert store.get_analysis(rid)==analysis


def test_actual_central_partial_career_update_keeps_twelve_runs(tmp_path):
    store=app.CentralStore(tmp_path/'central.sqlite3');old=central_row();new=copy.deepcopy(old)
    new['horses'][0]['allPastRuns']=new['horses'][0]['allPastRuns'][:5]
    store.upsert([old]);store.upsert([new])
    horse=store.races_json(old['date'])[0]['horses'][0]
    assert len(horse['allPastRuns'])==12 and len(horse['recentRaces'])==5
    store.conn.close()


@pytest.mark.parametrize('store_name',['PreparedRaceStore','RaceDataBank'])
def test_intentional_retention_difference_from_baseline_is_only_saved_ticket(tmp_path,store_name):
    detail=central_row();detail['preRaceBet']={'fixedAt':'before-off','items':[{'nums':[1]}]}
    outputs=[]
    for label,cls in [('old',legacy()[store_name]),('new',getattr(app,store_name))]:
        store=cls(tmp_path/(label+'.sqlite3'))
        write=(lambda value:store.put(value,force=True)) if store_name=='PreparedRaceStore' else store.upsert_race
        with patch('time.time',return_value=1_800_000_000):
            write(copy.deepcopy(detail));changed=copy.deepcopy(detail);changed['preRaceBet']={'items':[{'nums':[9]}]}
            write(changed)
        saved=store.get(detail['id'])[0] if store_name=='PreparedRaceStore' else store.get_race(detail['id'])[0]
        outputs.append(saved)
    assert outputs[0]['preRaceBet']=={'items':[{'nums':[9]}]}
    assert outputs[1]['preRaceBet']==detail['preRaceBet']
    # preparedMeta.revision intentionally hashes each original incoming update.
    assert {k:v for k,v in outputs[0].items() if k!='preRaceBet'}=={k:v for k,v in outputs[1].items() if k!='preRaceBet'}


def test_materialized_class_annotations_are_resolvable():
    import typing
    for record in METHODS:
        module=importlib.import_module(record['after'][:-3].replace('/','.'))
        method=getattr(getattr(module,record['owner']),record['method'])
        typing.get_type_hints(method)


def test_day_bundle_failed_refresh_cannot_delete_complete_known_data(tmp_path):
    store=app.DayBundleStore(tmp_path/'bundle.sqlite3')
    payload={'raceCount':1,'detailCount':1,'details':[central_row()]}
    store.put('2026-10-10',payload,True);first=store.get('2026-10-10')
    store.put('2026-10-10',{'raceCount':0,'detailCount':0,'details':[],'error':'timeout'},False)
    assert store.get('2026-10-10')==first
