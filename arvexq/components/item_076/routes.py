"""Forward each existing call once; implementation remains in its original module."""

def _parse_payouts(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
