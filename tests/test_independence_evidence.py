"""A sparse or invented deployment receipt must never count as a completion."""
from copy import deepcopy
import json
from pathlib import Path
from scripts.arvexq_independence_audit import audit

MANIFEST=json.loads(Path('docs/independence/requirements.json').read_text())

def test_exact_fixed_inventory_retains_all_200_items():
    result=audit(MANIFEST)
    assert not result['errors'] and result['total']==200
    assert result['complete']==0 and result['verdict']=='未完了'

def test_premature_completion_is_rejected_even_when_file_exists():
    proposed=deepcopy(MANIFEST);proposed['items'][0]['status']='本番検証済';proposed['completed']=1
    result=audit(proposed)
    assert result['errors'] and result['complete']==0 and result['verdict']=='未完了'

def test_duplicated_missing_requirement_cannot_be_hidden_in_count():
    proposed=deepcopy(MANIFEST);proposed['items'][99]['id']=1
    assert audit(proposed)['errors']
