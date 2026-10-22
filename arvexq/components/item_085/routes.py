"""Forward each existing call once; implementation remains in its original module."""

def _attach_nar_payouts(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _fetch_nar_payouts_only(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
