"""Forward each existing call once; implementation remains in its original module."""

def _prepared_ttl(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
