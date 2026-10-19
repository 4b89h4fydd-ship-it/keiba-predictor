"""Workflow responsibility ownership without running recovery or pushing main."""
from pathlib import Path
from arvexq.components.catalog import describe
from scripts.arvexq_components_audit import audit

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_commands_are_owned_but_never_executed_by_structure_tests():
    record = describe(150)
    assert record["state"] == "migrated-shared-context"
    assert len(record["owned_scripts"]) == 2
    workflow = (ROOT / ".github/workflows/arvexq-snapshot-recovery.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "bash arvexq/components/item_150/scripts/export_verified_originals.sh" in workflow
    assert "bash arvexq/components/item_150/scripts/commit_verified_originals.sh" in workflow
    assert "git push origin main" in (ROOT / record["owned_scripts"][1]).read_text()
    assert audit()["errors"] == []
