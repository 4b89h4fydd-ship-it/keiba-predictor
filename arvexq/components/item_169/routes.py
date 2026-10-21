"""Forward each existing call once; implementation remains in its original module."""

def environment_pack(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
