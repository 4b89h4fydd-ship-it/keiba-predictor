import pytest
from arvexq.features.readiness import diagnosis_ready

@pytest.mark.parametrize('prediction_status',['disabled','ready','missing',None])
def test_observed_diagnosis_independent_of_prediction(prediction_status):
    d={'preparedMeta':{'diagnosisReady':True},'predictionStatus':prediction_status}
    assert diagnosis_ready(d)
    d['preparedMeta']['diagnosisReady']=False
    assert not diagnosis_ready(d)

@pytest.mark.parametrize('value',[None,{}, {'preparedMeta':{}},{'preparedMeta':'invalid'},{'preparedMeta':{'diagnosisReady':'true'}}])
def test_missing_or_malformed_status_never_claims_ready(value):
    assert not diagnosis_ready(value)
