"""Forward each existing call once; implementation remains in its original module."""

def central_race_summaries(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def nar_race_summaries(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def races(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def track_pack(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
