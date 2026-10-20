from pathlib import Path
from arvexq.ingest.result_status.confirmed import official_confirmed

def test_confirmed_requires_unambiguous_official_status():
    assert official_confirmed("第8競走 確定")
    assert not official_confirmed("第8競走 速報")
    assert not official_confirmed("第8競走 暫定確定")
    assert not official_confirmed("第8競走 速報のち確定")
    assert not official_confirmed("出走表")

def test_nar_result_uses_independent_confirmation():
    source=__import__("inspect").getsource(__import__("arvexq.ingest.nar_result", fromlist=["parse_result_html"]))
    assert "explicit_final=official_confirmed(full)" in source
    assert "from arvexq.ingest.result_status.confirmed import official_confirmed" in source
