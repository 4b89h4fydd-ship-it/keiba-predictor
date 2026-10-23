from copy import deepcopy
from arvexq.forecast.publication import public_race


def frozen():
    race = {'id': 'nar-2026-10-23-園田-11', 'date': '2026-10-23', 'circuit': '地方',
            'startTime': '20:05', 'result': {'status': '確定'},
            'horses': [{'horseNumber': i, 'name': str(i)} for i in range(1, 7)],
            'predictionStatus': 'ready', 'predictionModelVersion': 'arvexq-stage64-product-v1'}
    race['prediction'] = {'modelVersion': 'arvexq-stage64-product-v1',
        'predictionStatus': 'ready', 'productionEligible': True,
        'raceId': race['id'], 'date': race['date']}
    race['predictionMarks'] = [{'horseNumber': i+1, 'mark': label}
        for i, label in enumerate('◎○▲△☆')]
    race['recommendedBets'] = [{'kind': '馬連', 'combos': [[1, 2]]}]
    return race


def test_postrace_keeps_original_stage64_and_original_input():
    source = frozen()
    before = deepcopy(source)
    out = public_race(source)
    assert out['predictionStatus'] == 'ready'
    assert out['recommendedBets'] == before['recommendedBets']
    assert out['predictionMarks'] == before['predictionMarks']
    assert [x['predMark'] for x in out['horses'][:5]] == list('◎○▲△☆')
    assert source == before


def test_no_unverified_postrace_creation():
    for modification in (
        lambda x: x.pop('prediction'),
        lambda x: x['prediction'].update(raceId='wrong'),
        lambda x: x['predictionMarks'][0].update(mark=''),
        lambda x: x['predictionMarks'][1].update(horseNumber=1),
        lambda x: x.update(predictionStatus='disabled'),
    ):
        source = frozen()
        modification(source)
        out = public_race(source)
        assert out['predictionStatus'] == 'disabled'
        assert 'recommendedBets' not in out
        assert 'predictionMarks' not in out
