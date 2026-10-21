"""Forward each existing call once; implementation remains in its original module."""

def _default_data_root(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _new_conn(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
