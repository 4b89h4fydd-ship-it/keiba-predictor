"""Forward each existing call once; implementation remains in its original module."""

def diagnosis_refresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def racedb_get_analysis(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def volatility_pack(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
