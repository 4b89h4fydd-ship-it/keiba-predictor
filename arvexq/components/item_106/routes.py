"""Forward each existing call once; implementation remains in its original module."""

def _race_volatility(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
