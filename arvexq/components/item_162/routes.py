"""Forward each existing call once; implementation remains in its original module."""

def _central_refresh_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def central_refresh_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def central_schema(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def central_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def collector_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def data_core_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def enrichment_schema(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def enrichment_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def local_refresh_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def odds_auto_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def prewarm_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def site_bootstrap_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
