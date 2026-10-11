"""RaceDB facade; each persistence responsibility has its own module."""
from .schema import RaceSchema
from .racecards import RaceCards
from .career import Career
from .odds import Odds
from .analysis import Analysis

class RaceDataBank(RaceSchema, RaceCards, Career, Odds, Analysis):
    pass
