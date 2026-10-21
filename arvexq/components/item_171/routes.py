"""Forward each existing call once; implementation remains in its original module."""

def racedb_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def snapshot_version(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def storage_status(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
