"""Check that D1 SQL rewrites are owned by #174 without changing entry imports."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_d1_implementation_has_single_owner():
    owned=(ROOT/"arvexq/components/item_174/d1_binding.mjs").read_text()
    shared=(ROOT/"arvexq/components/item_139/api_full_snapshot.mjs").read_text()
    legacy=(ROOT/"workers/api_full_snapshot.mjs").read_text()
    assert "export function rewriteDetailSQL(" in owned
    assert "export function storageEnvironment(" in owned
    assert "export {rewriteDetailSQL,storageEnvironment}" in shared
    assert "export {storageEnvironment}" in legacy
    assert "new Proxy(db" in owned
