"""Forward each existing call once; implementation remains in its original module."""

def _commercial_collect_once(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _commercial_collector_loop(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _data_core_cycle(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _data_core_loop(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _racedb_live_cycle(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _schedule_central_refresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _schedule_live_refresh(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _start_commercial_collector(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _start_data_core_collector(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _start_racedb_daemon(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
