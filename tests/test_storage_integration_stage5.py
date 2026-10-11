"""Real archive transport/SQLite and concurrent immutable storage integration."""
import copy
import csv
import io
import sqlite3
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import app
import pytest
from test_storage_stage5 import dump_db, legacy
from test_acquisition_integration import central_row


def archive_fixture():
    race=['']*66;horse=['']*33
    for key,value in {'track':'大井','date':'2026/10/10','race_no':'1','start_time':'15:00',
                      'title':'試験','distance':'1200','weather':'晴','condition':'良','field_size':'1','prize1':'100'}.items():
        race[app.RACE_IDX[key]]=value
    for key,value in {'track':'大井','date':'2026/10/10','race_no':'1','frame_no':'1','horse_no':'1',
                      'name':'試験馬','sex':'牡','age':'3','jockey':'騎手','carried_weight':'56',
                      'trainer':'調教師','finish':'1','time':'1:13.0'}.items():
        horse[app.HORSE_IDX[key]]=value
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as bundle:
        for name,row in [('fixture_racelist.csv',race),('fixture_horselist.csv',horse)]:
            text=io.StringIO();csv.writer(text).writerow(row)
            bundle.writestr(name,text.getvalue().encode('cp932'))
    return archive.getvalue()


def test_actual_zip_to_nar_db_download_cache_and_failure_match_baseline(tmp_path):
    import arvexq.storage.nar.sync as sync_module
    outputs=[];databases=[];calls=[]
    for label in ('old','new'):
        namespace=legacy();archive=tmp_path/label/'archives';path=tmp_path/label/'nar.sqlite3'
        namespace['ARCHIVE_DIR']=archive
        cls=namespace['NarSync'] if label=='old' else sync_module.NarSync
        store=namespace['NarStore'](path) if label=='old' else app.NarStore(path)
        requests=[]
        def fetch(request,timeout):
            requests.append((request.full_url,dict(request.header_items()),timeout))
            return io.BytesIO(archive_fixture())
        with patch.object(sync_module,'ARCHIVE_DIR',archive),patch('time.time',return_value=1_800_000_000), \
             patch('urllib.request.urlopen',side_effect=fetch):
            sync=cls(store=store)
            result=[sync.sync_daily(force=True),sync.sync_daily(),sync.sync_month(2025,9,force=True),sync.sync_month(2025,9)]
            assert len(requests)==2 and all(r[-1]==45 for r in requests)
            before=dump_db(path)
            with patch('urllib.request.urlopen',side_effect=TimeoutError('fixture')):
                with pytest.raises(TimeoutError):sync.sync_daily(force=True)
            assert dump_db(path)==before
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'not a zip')):
                with pytest.raises(RuntimeError,match='not a ZIP'):sync.sync_daily(force=True)
            assert dump_db(path)==before
            result.append(store.races_json('2026-10-10'))
            assert result[-1][0]['horses'][0]['name']=='試験馬'
            outputs.append(result);calls.append(requests)
        store.conn.close()
        # archive_path contains isolated temporary paths; normalize only this operational column.
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE sync_log SET archive_path='fixture'")
        databases.append(dump_db(path))
    assert outputs[0]==outputs[1] and calls[0]==calls[1] and databases[0]==databases[1]


@pytest.mark.parametrize('store_name',['PreparedRaceStore','RaceDataBank'])
def test_concurrent_first_ticket_is_immutable_on_reopen(tmp_path,store_name):
    path=tmp_path/'concurrent.sqlite3';store=getattr(app,store_name)(path)
    barrier=threading.Barrier(2)
    def update(number):
        payload=central_row();payload['preRaceBet']={'fixedAt':'before-off','items':[{'nums':[number]}]}
        barrier.wait(timeout=10)
        if store_name=='PreparedRaceStore':store.put(payload,force=True)
        else:store.upsert_race(payload)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(update,[1,2]))
    read=store.get if store_name=='PreparedRaceStore' else store.get_race
    detail=read(central_row()['id'])[0];first=copy.deepcopy(detail['preRaceBet'])
    assert first['items'][0]['nums'] in ([1],[2])
    reopened=getattr(app,store_name)(path)
    detail['preRaceBet']={'items':[{'nums':[9]}]}
    if store_name=='PreparedRaceStore':reopened.put(detail,force=True)
    else:reopened.upsert_race(detail)
    read=reopened.get if store_name=='PreparedRaceStore' else reopened.get_race
    assert read(detail['id'])[0]['preRaceBet']==first
