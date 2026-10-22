"""Forward each existing call once; implementation remains in its original module."""

def race_detail(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def racedb_race(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
