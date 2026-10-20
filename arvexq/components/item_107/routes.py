"""Forward each existing call once; implementation remains in its original module."""

def _attach_evaluation_context(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
