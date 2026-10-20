"""Offline provider ownership and unchanged acquisition/DOM handoff contracts."""
import copy
from unittest.mock import patch
import pytest
from bs4 import BeautifulSoup
from arvexq.ingest.nar_odds import parse_live_odds_html
from arvexq.ingest.nar_result import parse_result_html as parse_nar_result
from arvexq.ingest.payouts import parse_payouts
from arvexq.ingest.field_normalization import _scratch_status


def clean(value):
    return ' '.join(str(value or '').split())


def result_html(status='確定', runners=3):
    headers=['着順','枠','馬番','馬名','馬体重','タイム','コーナー','人気','単勝']
    rows=['<tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr>']
    for i in range(1,runners+1):
        cells=[str(i),str(i),str(i),'競走馬'+str(i),'480(+2)','1:33.2','3-2-1','2','4.2']
        rows.append('<tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>')
    return '<h2>競走成績 '+status+'</h2><p>天候：小雨 馬場：稍重</p><table>'+''.join(rows)+'</table>'


@pytest.mark.parametrize('status,expected',[('確定','確定'),('速報','速報'),('暫定確定','速報')])
def test_nar_result_dom_runs_without_transport_and_keeps_confirmation_separate(status,expected):
    known={'競走馬'+str(i):i for i in range(1,4)};before=copy.deepcopy(known)
    with patch('urllib.request.urlopen',side_effect=AssertionError('parser performed I/O')):
        actual=parse_nar_result(result_html(status),known=known,clean=clean,
            parse_payouts=parse_payouts,clean_weather=clean,clean_condition=clean)
    assert actual['status']==expected
    assert actual['weather']=='小雨' and actual['condition']=='稍重'
    assert actual['finishers'][0]['cornerPositions']==[3,2,1]
    assert actual['finishers'][0]['bodyWeightChange']==2
    assert actual['finishers'][0]['last3FSeconds'] is None
    assert known==before


def test_partial_nar_page_does_not_publish_a_podium():
    assert parse_nar_result(result_html(runners=2),known={},clean=clean,
        parse_payouts=parse_payouts,clean_weather=clean,clean_condition=clean) is None


def test_nar_market_dom_has_no_fetch_or_forecast_dependency():
    html='<table><tr>'+''.join('<th>'+x+'</th>' for x in ['枠','馬番','馬名','単勝','複勝下限','複勝上限','性齢','馬体重'])+'</tr>'
    for no,odds in [(1,'4.2'),(2,'取消'),(3,'4.2')]:
        html+='<tr>'+''.join('<td>'+x+'</td>' for x in ['1',str(no),'競走馬',odds,'1.1','2.4','牡3','480(+2)'])+'</tr>'
    with patch('urllib.request.urlopen',side_effect=AssertionError('parser performed I/O')):
        out=parse_live_odds_html(html+'</table>',clean=clean,parse_scratch_status=_scratch_status)
    assert out[1]['winOdds']==out[3]['winOdds']==4.2
    assert out[1]['popularity']==out[3]['popularity']==1
    assert out[1]['placeOddsLow']==1.1 and out[1]['placeOddsHigh']==2.4
    assert out[2]['scratched'] and out[2]['winOdds'] is None


@pytest.mark.parametrize('label,kind,combo',[('単勝','単勝','1'),('複勝','複勝','2'),
    ('枠複','枠連','1-2'),('馬複','馬連','1-3'),('ワイド','ワイド','1-3'),
    ('馬連単','馬単','3→1'),('三連複','3連複','1-2-3'),('３連単','3連単','3→2→1')])
def test_eight_observed_payout_kinds_preserve_source_order_and_do_not_mutate_dom(label,kind,combo):
    row='<tr><th>'+label+'</th><td>'+combo+'</td><td>1,230円</td></tr>'
    soup=BeautifulSoup('<table>'+row+row+'</table>','html.parser');before=str(soup)
    assert parse_payouts(soup)==[{'type':kind,'combination':combo,'amount':1230}]
    assert str(soup)==before


def test_existing_app_caller_passes_acquired_html_and_retains_source_url():
    import io
    import app
    detail={'id':'nar-2026-10-10-大井-01','track':'大井','date':'2026-10-10','raceNumber':1,'horses':[]}
    before=copy.deepcopy(detail)
    with patch.object(app.urllib.request,'urlopen',return_value=io.BytesIO(result_html().encode('cp932'))) as fetch:
        actual=app._nar_official_result_fast(detail)
    assert fetch.call_count==1
    assert actual['sourceUrl'].startswith('https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?')
    assert detail==before


def test_jra_existing_fetch_preserves_strict_error_policy():
    import app
    with patch.object(app,'_jra_request',side_effect=TimeoutError('offline')):
        assert app._jra_parse_result('observed-id') is None
        with pytest.raises(TimeoutError):app._jra_parse_result('observed-id',strict_errors=True)


def test_jra_result_dom_keeps_its_source_fields_and_calls_existing_acquisition_once():
    import app
    headers=['着順','枠','馬番','馬名','タイム','着差','推定上り','コーナー通過順位','馬体重','人気']
    rows=[]
    for i in range(1,4):
        cells=[str(i),str(i),str(i),'中央馬'+str(i),'1:33.2','ハナ','37.2','2-2-1','480(+2)','2']
        rows.append('<tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>')
    html='<h2>観測済競走</h2><p>確定</p><table><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr>'+''.join(rows)+'</table>'
    base={'date':'2026-10-18','track':'東京','raceNumber':3,'surface':'芝','distance':1600}
    before=copy.deepcopy(base)
    with patch.object(app,'_jra_request',return_value=html) as fetch:
        out=app._jra_parse_result('unknown-identifier',base)
    fetch.assert_called_once_with('https://www.jra.go.jp/JRADB/accessS.html','unknown-identifier',20)
    assert out['track']=='東京' and out['distance']==1600
    assert out['result']['source']=='JRA公式'
    assert out['result']['finishers'][0]['marginText']=='ハナ'
    assert out['result']['finishers'][0]['timeSeconds']==93.2
    assert out['result']['finishers'][0]['last3FRank']==1
    assert base==before


def test_nar_multiline_payout_cells_keep_observed_combination_amount_pairs():
    soup=BeautifulSoup('<table><tr><th>複勝</th><td>1<br>2<br>3</td><td>120円<br>230円<br>340円</td></tr></table>','html.parser')
    assert parse_payouts(soup)==[{'type':'複勝','combination':str(no),'amount':amount}
        for no,amount in [(1,120),(2,230),(3,340)]]
