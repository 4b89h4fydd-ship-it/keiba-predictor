"""#66 Isolated observed market delta. Unknown observations are not zeros."""
from .missing import valid_win_odds

def win_odds_delta(previous, current):
    if not valid_win_odds(previous) or not valid_win_odds(current):return None
    return round(float(current)-float(previous),6)
