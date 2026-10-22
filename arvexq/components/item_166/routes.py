"""Forward each existing call once; implementation remains in its original module."""

def past_pack(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
