from copy import deepcopy
import pytest
from pathlib import Path
from arvexq.forecast.inputs import prediction_input
from arvexq.forecast.publication import public_race

@pytest.mark.parametrize('circuit',['中央','地方'])
def test_old_snapshots_cannot_publish_but_facts_and_source_archive_survive(circuit):
    original={'id':'race','circuit':circuit,'preRacePrediction':{'horses':[{'mark':'◎'}]},
              'preRaceBet':{'tickets':[[1,2,3]]},'forecastRevisions':[{'mark':'◎'}],
              'currentForecastRevisionId':'old','horses':[{'horseNumber':1,'name':'テスト','mark':'◎','winOdds':2.5,'recentRaces':[{'date':'2026-09-01','finish':1}]}],
              'raceCardView':[{'mark':'◎','name':'テスト'}],'result':{'status':'確定','payouts':[{'type':'単勝','amount':250}]}}
    before=deepcopy(original);result=public_race(original)
    assert result['predictionStatus']=='disabled'
    assert all(k not in result for k in ('preRacePrediction','preRaceBet','forecastRevisions','currentForecastRevisionId'))
    assert 'mark' not in result['raceCardView'][0] and 'mark' not in result['horses'][0]
    assert result['result']==original['result'] and result['horses'][0]['recentRaces']==original['horses'][0]['recentRaces']
    result['horses'][0]['name']='changed'
    assert original==before

def test_three_engines_are_independent_and_empty_without_approval():
    facts=prediction_input({'id':'race','result':{'status':'確定'},'horses':[{'horseNumber':1,'name':'テスト','mark':'◎','integratedEvaluation':{'score':99}}]})
    assert 'result' not in facts and 'mark' not in facts['horses'][0]
    assert 'result' not in facts
    root=Path(__file__).resolve().parents[1]
    assert not (root/'arvexq/forecast/tickets.py').exists()
    assert 'def generate_marks(' not in (root/'arvexq/forecast/marks.py').read_text(encoding='utf-8')
