"""#69 Missing observed odds state. Never fill gaps from predicted prices."""
import math

def valid_win_odds(value):
    if isinstance(value,bool) or value is None: return False
    try: value=float(value)
    except (TypeError,ValueError): return False
    return math.isfinite(value) and value>0

def odds_missing(horse):
    return not isinstance(horse,dict) or not valid_win_odds(horse.get("winOdds"))
