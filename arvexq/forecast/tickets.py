"""Project tickets from the SAME calibrated joint finish distribution as marks."""
from copy import deepcopy

def generate_tickets(prediction, marks=None, quoted_odds=None, **_):
    if not isinstance(prediction,dict) or prediction.get("predictionStatus")!="ready":
        return []
    # No invented odds or synthetic positive-EV tickets. Internal odds must
    # have entered the forecaster BEFORE the event, not at public read time.
    return deepcopy(prediction.get("tickets") or [])
