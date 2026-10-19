"""Deprecated import adapters. Production has no prediction model installed."""
VERSION = 'arvexq-retired-assistant-rank-baseline'
from arvexq.forecast.marks import clear_marks

NAR_MODEL_VERSION = JRA_MODEL_VERSION = MODEL_VERSION = VERSION

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


def model_version(race):
    return MODEL_VERSION
