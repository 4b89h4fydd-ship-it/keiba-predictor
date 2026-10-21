"""Forward each existing call once; implementation remains in its original module."""

def _jra_parse_past_cell(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
