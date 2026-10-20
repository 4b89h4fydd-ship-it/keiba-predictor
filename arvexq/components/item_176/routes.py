"""Forward each existing call once; implementation remains in its original module."""

def home(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
