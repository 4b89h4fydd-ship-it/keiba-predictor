"""Retired candidates must not interrupt the existing factual publication job."""
from pathlib import Path
import ast
import re
import yaml
ROOT=Path(__file__).resolve().parents[1]


def test_prefetch_no_longer_executes_deleted_candidate_generators():
    config=yaml.safe_load((ROOT/'.github/workflows/arvexq-prefetch.yml').read_text())
    steps=[s for j in config['jobs'].values() for s in j['steps']]
    runs='\n'.join(str(s.get('run','')) for s in steps)
    for script in ('arvexq_capture_batch_research.py','arvexq_apply_learned_overlay.py'):
        assert script not in runs
    assert 'prefetch-learned.json' not in runs
    # The same existing factual pipeline still prepares, protects, syncs and
    # verifies the actual racecards. Retiring a model must not remove these gates.
    for script in ('arvexq_prefetch.py','arvexq_protect_sync.py','arvexq_sync_batches.py','arvexq_fetch_d1_bundle.py'):
        assert script in runs
    for guard in ('D1 racecard delivery incomplete','D1_MISSING_CARDS','missing_summary_ids','prepared_horses'):
        assert guard in runs


def test_live_workflows_do_not_invoke_removed_python_entrypoints():
    missing=[]
    for path in (ROOT/'.github/workflows').glob('*.yml'):
        config=yaml.safe_load(path.read_text())
        for job in config.get('jobs',{}).values():
            for step in job.get('steps',[]):
                for script in re.findall(r'\bpython\s+(?:-u\s+)?((?:scripts|arvexq)/[\w/.-]+\.py)\b',str(step.get('run',''))):
                    if not (ROOT/script).is_file():missing.append((path.name,script))
    assert missing==[]


def test_retired_model_audit_runner_is_archived_verbatim():
    assert not (ROOT/'.github/workflows/arvexq-foundation-audit.yml').exists()
    archived=ROOT/'docs/research/retired-workflows/arvexq-foundation-audit.yml'
    config=yaml.safe_load(archived.read_text())
    assert config['name']=='ARVEXQ Prediction Audits'
    assert len(config['jobs']['audit']['steps'])==5
    # Research implementations remain; they are not silently replaced by a
    # different ranker or deleted as if they were race data.
    for name in ('arvexq_foundation_priority_audit.py','arvexq_signal_dedup_audit.py','arvexq_signal_dedup_multiday_audit.py'):
        assert (ROOT/'scripts'/name).is_file()
