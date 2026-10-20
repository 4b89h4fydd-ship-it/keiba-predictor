from stage4_source_support import implementation_source
from pathlib import Path
from arvexq.ingest.result_status.confirmed import official_confirmed

def test_confirmed_requires_unambiguous_official_status():
    assert official_confirmed("第8競走 確定")
    assert not official_confirmed("第8競走 速報")
    assert not official_confirmed("第8競走 暫定確定")
    assert not official_confirmed("第8競走 速報のち確定")
    assert not official_confirmed("出走表")

def test_nar_result_uses_independent_confirmation():
    source=implementation_source()
    assert "explicit_final=official_confirmed(full)" in source
    from arvexq.components.item_073.confirmed import official_confirmed as connected
    assert connected is official_confirmed
