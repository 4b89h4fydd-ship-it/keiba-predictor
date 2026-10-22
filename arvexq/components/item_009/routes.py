"""Forward each existing call once; implementation remains in its original module."""

def _jra_track_from_cname(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
