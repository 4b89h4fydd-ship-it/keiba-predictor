"""Forward each existing call once; implementation remains in its original module."""

def payout_refresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
