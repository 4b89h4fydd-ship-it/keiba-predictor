"""Check original status/HTTP contracts and public structural audit import."""
from scripts.arvexq_components_audit import audit
from arvexq.components.item_196.audit import audit as owned_audit
from arvexq.ingest.result_status.confirmed import official_confirmed
from arvexq.components.item_074.provisional import has_provisional_marker
from arvexq.components.item_175.http_policy import retryable_readback_status, display_fallback_status


def test_audit_uses_owned_function():
    assert audit is owned_audit


def test_provisional_status_rejects_mixed_official_labels():
    assert official_confirmed("第8競走 確定")
    assert has_provisional_marker("速報のち確定")
    assert not official_confirmed("速報のち確定")


def test_http_status_sets_stay_identical():
    assert [x for x in range(400,600) if retryable_readback_status(x)] == [408,500,502,503,504]
    assert [x for x in range(400,600) if display_fallback_status(x)] == [404,503]
