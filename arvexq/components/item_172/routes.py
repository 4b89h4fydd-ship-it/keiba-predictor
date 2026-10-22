"""Forward each existing call once; implementation remains in its original module."""

def health(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def runtime_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
