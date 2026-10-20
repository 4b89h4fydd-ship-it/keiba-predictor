"""Forward each existing call once; implementation remains in its original module."""

def model_audit(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def model_learning(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
