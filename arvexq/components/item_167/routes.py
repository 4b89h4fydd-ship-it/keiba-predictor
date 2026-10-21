"""Forward each existing call once; implementation remains in its original module."""

def collect_race_info(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def odds_refresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
