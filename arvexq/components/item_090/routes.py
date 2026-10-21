"""Forward each existing call once; implementation remains in its original module."""

def _pc_fit_metrics(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
