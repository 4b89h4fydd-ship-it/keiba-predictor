"""Forward each existing call once; implementation remains in its original module."""

def _attach_local_volatility_to_summaries(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _compute_local_volatility_for_race(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _ensure_race_volatility(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _local_volatility_map(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
