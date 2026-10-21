"""Forward each existing call once; implementation remains in its original module."""

def _merge_live_market_rows(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
