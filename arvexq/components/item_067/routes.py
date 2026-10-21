"""Forward each existing call once; implementation remains in its original module."""

def _restore_saved_odds(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
