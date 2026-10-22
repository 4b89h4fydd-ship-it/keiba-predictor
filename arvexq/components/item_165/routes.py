"""Forward each existing call once; implementation remains in its original module."""

def horse_snapshot(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
