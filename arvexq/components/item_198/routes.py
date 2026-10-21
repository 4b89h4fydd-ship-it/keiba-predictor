"""Forward each existing call once; implementation remains in its original module."""

def appjs(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
