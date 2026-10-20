"""Focused equivalence and cross-circuit safety checks for cache policy ownership."""
import pytest
from arvexq.v3.transport.cache import factual_cache_key, freshness
from arvexq.components.item_146.cache_key import factual_cache_key as owned_cache_key
from arvexq.components.item_161.freshness import freshness as owned_freshness


def test_public_cache_functions_use_exact_owned_implementation_objects():
    assert factual_cache_key is owned_cache_key
    assert freshness is owned_freshness


def test_cache_identity_keeps_jra_and_nar_separate():
    jra = factual_cache_key("jra-20261020-test-1", "jra")
    nar = factual_cache_key("nar-20261020-test-1", "nar")
    assert jra != nar
    for race_id, circuit in (("jra-20261020-test-1", "nar"), ("nar-20261020-test-1", "jra"), ("not-prefixed", "jra")):
        with pytest.raises(ValueError): factual_cache_key(race_id, circuit)


def test_freshness_boundaries_and_missing_values_are_unchanged():
    assert freshness(100, now_epoch=109, ttl_seconds=10) == "fresh"
    assert freshness(100, now_epoch=110, ttl_seconds=10) == "stale"
    assert freshness(111, now_epoch=110, ttl_seconds=10) == "clock-conflict"
    assert freshness(None, now_epoch=110, ttl_seconds=10) == "unknown"
    with pytest.raises(ValueError): freshness(100, now_epoch=110, ttl_seconds=-1)
