"""87: Observation readiness must not depend on a disabled prediction engine."""
def diagnosis_ready(detail):
    """Stored race -> readiness flag produced by observed-history diagnostics.

    Prediction readiness, probability coverage and model IDs are deliberately
    outside this contract. This does not assert complete lifetime history.
    """
    if not isinstance(detail, dict): return False
    meta = detail.get('preparedMeta')
    return isinstance(meta, dict) and meta.get('diagnosisReady') is True
