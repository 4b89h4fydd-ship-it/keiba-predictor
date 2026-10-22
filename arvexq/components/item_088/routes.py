"""Forward each existing call once; implementation remains in its original module."""

def _pc_clamp(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _pc_finish_quality(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _pc_list_quality(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _pc_race_field(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
