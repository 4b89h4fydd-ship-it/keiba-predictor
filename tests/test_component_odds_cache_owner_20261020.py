from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_odds_cache_ownership_and_public_ttls():
    owner=(ROOT/"arvexq/components/item_145/odds_cache.mjs").read_text()
    worker=(ROOT/"arvexq/components/item_173/web.mjs").read_text()
    assert "max-age=604800" in owner
    assert "max-age=15" in worker
    assert "cacheLookup(cache,key" in worker
    assert "cacheSave(cache,key,retainedKey,response,ctx)" in worker
    assert "retainedLookup(caches.default,retainedKey)" in worker
    assert "const retained=response.clone()" not in worker
