"""Forward each existing call once; implementation remains in its original module."""

def _jra_merge_run_fields(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _jra_merge_runs(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
