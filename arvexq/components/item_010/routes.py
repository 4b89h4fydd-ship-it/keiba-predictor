"""Forward each existing call once; implementation remains in its original module."""

def _jra_program_lookup(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _jra_program_summaries(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
