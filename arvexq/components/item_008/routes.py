"""Forward each existing call once; implementation remains in its original module."""

def normalize_central_race(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
