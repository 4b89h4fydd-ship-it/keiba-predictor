"""Forward each existing call once; implementation remains in its original module."""

def _pc_sectional_score(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
