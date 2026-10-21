"""Forward each existing call once; implementation remains in its original module."""

def _is_jump_run(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
