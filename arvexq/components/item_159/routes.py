"""Forward each existing call once; implementation remains in its original module."""

def _ensure_detail_background_jobs(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _ensure_fast_card_workers(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _fast_card_worker(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _prepare_race_snapshot(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _queue_fast_card(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _schedule_detail_background_jobs(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def prepare_race(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
