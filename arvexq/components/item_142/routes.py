"""Forward each existing call once; implementation remains in its original module."""

def _data_core_snapshot(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _prepared_get_fresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _racedb_get_fast(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
