from arvexq.ingest.entry_fields import cancellation, race_excluded

def test_observed_entry_statuses():
    assert cancellation.from_status("出走取消")
    assert not cancellation.from_status("除外")
    assert race_excluded.from_status("除外")
    assert not race_excluded.from_status("出走取消")
    assert not race_excluded.from_status("")
