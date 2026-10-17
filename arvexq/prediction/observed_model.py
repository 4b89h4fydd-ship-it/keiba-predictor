"""Deprecated import adapters. Production has no prediction model installed."""
from arvexq.forecast.engine import VERSION, build_prediction
from arvexq.forecast.marks import clear_marks

NAR_MODEL_VERSION = JRA_MODEL_VERSION = MODEL_VERSION = VERSION

def model_version(race):
    return VERSION

def rank_observed(horses, race):
    return []

def rank_nar(horses, race):
    if race.get('circuit') not in ('地方', 'NAR', 'nar', 'local'):
        raise ValueError('NAR adapter requires NAR race')
    return []

def rank_jra(horses, race):
    if race.get('circuit') not in ('中央', 'JRA', 'jra', 'central'):
        raise ValueError('JRA adapter requires JRA race')
    return []

def apply_observed_marks(detail):
    clear_marks(detail)
    if isinstance(detail, dict):
        detail['predictionStatus'] = 'disabled'
        detail['predictionModelVersion'] = VERSION
        detail['markEngineVersion'] = VERSION
    return detail

def apply_nar_marks(detail):
    if isinstance(detail, dict) and detail.get('circuit') not in ('地方', 'NAR', 'nar', 'local'):
        raise ValueError('NAR adapter requires NAR race')
    return apply_observed_marks(detail)
