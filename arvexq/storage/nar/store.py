"""NAR facade: imports, history and racecards share one connection per instance."""
from .schema import NarSchema
from .imports import NarImports
from .history import NarHistory
from .racecards import NarRacecards

class NarStore(NarSchema, NarImports, NarHistory, NarRacecards):
    pass
