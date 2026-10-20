"""Forward each existing call once; implementation remains in its original module."""

def _snapshot_final(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
