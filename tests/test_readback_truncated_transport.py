"""Retry incomplete transfers on the existing URL without weakening validation."""
import http.client
import io
import json
import pytest
from arvexq.ingest import d1_day_readback as reader
URL='https://example.invalid/api/race/nar-2026-10-20-浦和-02'


def opener_for(responses,calls):
    def open_(request,timeout):
        calls.append(request.full_url)
        value=responses.pop(0)
        if isinstance(value,Exception):raise value
        return io.BytesIO(value)
    return open_


@pytest.mark.parametrize('partial',[b'{"detail":{"name":"cut',b'{"name":"\xe6\x9d',http.client.IncompleteRead(b'{',100)])
def test_incomplete_body_retries_identical_route_and_restores_full_record(partial):
    calls=[]
    source={'ok':True,'detail':{'id':'nar-2026-10-20-浦和-02','horses':[{'horseNumber':1,'name':'原本'}]}}
    result=reader.get_json(URL,opener=opener_for([partial,json.dumps(source,ensure_ascii=False).encode()],calls),sleeper=lambda _:None)
    assert result==source
    assert calls==[URL,URL]


def test_repeated_truncation_fails_with_existing_two_attempt_limit():
    calls=[]
    with pytest.raises(json.JSONDecodeError):
        reader.get_json(URL,opener=opener_for([b'{',b'{'],calls),sleeper=lambda _:None)
    assert calls==[URL,URL]


def test_valid_json_wrong_schema_is_not_retried_as_transport_failure():
    calls=[]
    with pytest.raises(ValueError,match='must be an object'):
        reader.get_json(URL,opener=opener_for([b'[]'],calls),sleeper=lambda _:None)
    assert calls==[URL]


def test_oversized_body_is_not_retried_or_accepted(monkeypatch):
    monkeypatch.setattr(reader,'MAX_RESPONSE_BYTES',8)
    calls=[]
    with pytest.raises(ValueError,match='exceeds read budget'):
        reader.get_json(URL,opener=opener_for([b'123456789'],calls),sleeper=lambda _:None)
    assert calls==[URL]


def test_short_reads_before_eof_preserve_large_race_without_extra_request():
    source={'ok':True,'detail':{'id':'nar-2026-10-20-浦和-02',
                              'allPastRuns':[{'name':'原本','payload':'x'*1300} for _ in range(200)]}}
    raw=json.dumps(source,ensure_ascii=False).encode()
    class ShortResponse(io.BytesIO):
        def read(self,size=-1):
            return super().read(min(size,131072))
    calls=[]
    def open_(request,timeout):
        calls.append(request.full_url)
        return ShortResponse(raw)
    result=reader.get_json(URL,opener=open_,sleeper=lambda _:None)
    assert result==source
    assert calls==[URL]


def test_429_is_not_retried_to_avoid_aggravating_rate_limit():
    import urllib.error
    calls=[]
    rate_limited=urllib.error.HTTPError(URL,429,'too many requests',{},None)
    with pytest.raises(urllib.error.HTTPError) as exc:
        reader.get_json(URL,opener=opener_for([rate_limited],calls),sleeper=lambda _:None)
    assert exc.value.code==429
    assert calls==[URL]
