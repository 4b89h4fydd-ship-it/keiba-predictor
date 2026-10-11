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
    target = ast.parse((ROOT / record['after']).read_text())
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
    modules=sorted({r['after'][:-3].replace('/','.') for r in METHODS+FUNCTIONS})
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
