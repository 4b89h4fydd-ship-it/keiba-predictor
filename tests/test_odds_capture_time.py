from stage4_source_support import implementation_source
from datetime import datetime,timezone,timedelta
import pytest
from pathlib import Path
from arvexq.ingest.odds_capture_time import odds_observed_at

def test_observed_time_is_jst_not_server_timezone():
    assert odds_observed_at(datetime(2026,10,18,0,30,tzinfo=timezone.utc))=="09:30:00"
    assert odds_observed_at(datetime(2026,10,18,9,30,tzinfo=timezone(timedelta(hours=9))))=="09:30:00"
    with pytest.raises(ValueError): odds_observed_at(datetime(2026,10,18,9,30))

def test_nar_odds_recording_calls_standalone_clock():
    app=implementation_source()
    fn=app.split("def _attach_nar_live_odds(",1)[1].split("\ndef ",1)[0]
    assert 'detail["oddsUpdatedAt"]=odds_observed_at()' in fn
