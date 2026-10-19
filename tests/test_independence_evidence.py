"""A sparse or invented deployment receipt must never count as a completion."""
from copy import deepcopy
import json
from pathlib import Path
from scripts.arvexq_independence_audit import audit

MANIFEST=json.loads(Path('docs/independence/requirements.json').read_text())

def test_exact_fixed_inventory_retains_all_200_items():
    result=audit(MANIFEST)
    assert not result['errors'] and result['total']==200
    assert result['complete']==3 and result['verdict']=='未完了'

def test_premature_completion_is_rejected_even_when_file_exists():
    proposed=deepcopy(MANIFEST);proposed['items'][0]['status']='本番検証済';proposed['completed']=3
    proposed['items'][1]['status']='本番検証済'
    proposed['items'][1]['evidence']=None
    result=audit(proposed)
    assert result['errors'] and result['complete']==2 and result['verdict']=='未完了'

def test_duplicated_missing_requirement_cannot_be_hidden_in_count():
    proposed=deepcopy(MANIFEST);proposed['items'][99]['id']=1
    assert audit(proposed)['errors']

def test_waiting_prediction_calculation_never_counts_as_completed():
    proposed=deepcopy(MANIFEST)
    item=proposed['items'][111]
    item['status']='予想ロジック仕様待ち'
    item['owner']='別チャット'
    item['prediction_logic_status']='予想ロジック仕様待ち'
    result=audit(proposed)
    assert not result['errors']
    assert result['complete']==3 and result['verdict']=='未完了'

def test_waiting_status_cannot_hide_a_codex_responsibility():
    proposed=deepcopy(MANIFEST)
    proposed['items'][0]['status']='予想ロジック仕様待ち'
    proposed['items'][0]['owner']='Codex'
    assert audit(proposed)['errors']

def test_version_two_requires_a_boundary_for_every_item():
    proposed=deepcopy(MANIFEST)
    proposed['version']=2
    for item in proposed['items']:
        item['owner']='Codex'
        item['prediction_logic_status']='対象外'
        if item['status']=='予想ロジック仕様待ち':
            item['status']='未着手'
    assert not audit(proposed)['errors']
    proposed['items'][199].pop('owner')
    assert audit(proposed)['errors']


def test_status_counts_reconcile_without_promoting_partial_work():
    report = audit(MANIFEST)
    counts = report['state_counts']
    assert counts['本番検証済'] == 3
    assert counts['分離済'] == 8
    assert counts['解析済'] == 61
    assert counts['main統合済'] == 3
    assert counts['未着手'] == 96
    assert counts['予想ロジック仕様待ち'] == 29
    assert report['partial'] == 72
    assert report['not_started_or_waiting'] == 125
    assert report['unclassified'] == 0
    assert report['complete'] + report['partial'] + report['not_started_or_waiting'] == 200
