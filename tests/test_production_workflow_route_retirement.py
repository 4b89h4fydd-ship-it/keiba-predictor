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



def test_obihiro_excluded_at_existing_public_race_and_track_entries():
    """Retired Banei races must not enter normal lists or detail read paths."""
    race=(ROOT/'arvexq/components/item_163/implementation.py').read_text()
    worker=(ROOT/'arvexq/components/item_173/api.mjs').read_text()
    preserved=(ROOT/'workers/api_preserved.mjs').read_text()
    bootstrap=(ROOT/'arvexq/components/item_141/implementation.py').read_text()
    refresh=(ROOT/'arvexq/components/item_151/implementation.py').read_text()
    assert 'if track in ("帯広", "帯広ば"):' in race
    assert "r.track NOT IN ('帯広','帯広ば')" in race
    assert "track NOT IN ('帯広','帯広ば')" in preserved
    assert "const activeSummaries = summaries.filter(activeRace);" in preserved
    assert "const activeDetails = details.filter(activeRace);" in preserved
    assert "const activeCurrent = oddsCurrent.filter(activeRace);" in preserved
    assert "const activeHistory = oddsHistory.filter(activeRace);" in preserved
    assert "race venue excluded" in worker
    assert "url.pathname.startsWith('/api/odds/')" in worker
    assert 'str(r.get("track") or "") in ("帯広", "帯広ば")' in bootstrap
    assert "race venue excluded" in refresh
    assert 'str(r.get("track") or "") not in ("帯広", "帯広ば")' in refresh
