"""Coverage for final structurally mapped items, without production side effects."""
from pathlib import Path
from arvexq.components.item_199.deploy_contract import inspect_deploy_workflows
from arvexq.components.catalog import all_components,assemble_ui

ROOT=Path(__file__).resolve().parents[1]


def test_deploy_contract_performs_no_deployment():
    record=inspect_deploy_workflows()
    assert record["deployment_executed"] is False
    assert record["production_verified"] is False
    assert all(row["present"] and row["content"] for row in record["workflows"].values())


def test_no_mapped_only_state_remains():
    assert not [x for x in all_components() if x["state"]=="mapped-existing-source"]
    assert assemble_ui()==(ROOT/"arvexq/ui/static/app.js").read_text(encoding="utf-8")
