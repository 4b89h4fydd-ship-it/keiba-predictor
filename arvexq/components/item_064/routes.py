"""Forward each existing call once; implementation remains in its original module."""

def _attach_nar_live_odds(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _nar_live_odds(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)

def _parse_nar_live_odds_html(implementation, /, *args, **kwargs):
    return implementation(*args, **kwargs)
