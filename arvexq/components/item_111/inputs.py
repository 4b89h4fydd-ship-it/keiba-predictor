"""111: Immutable facts supplied to production prediction adapters."""
from copy import deepcopy

RACE_FIELDS = ('id', 'date', 'track', 'raceNumber', 'startTime', 'circuit', 'surface', 'distance', 'condition', 'weather')
HORSE_FIELDS = ('horseNumber', 'frameNumber', 'name', 'sex', 'age', 'jockey', 'trainer', 'affiliation', 'carriedWeight', 'bodyWeight', 'bodyWeightChange', 'status', 'scratched', 'withdrawn', 'recentRaces', 'allPastRuns')

def prediction_input(detail):
    """Mapping -> copied fact DTO; old scores/marks/results are never inputs."""
    if not isinstance(detail, dict): return {'horses': []}
    result = {key: deepcopy(detail[key]) for key in RACE_FIELDS if key in detail}
    result['horses'] = [{key: deepcopy(h[key]) for key in HORSE_FIELDS if key in h}
                        for h in (detail.get('horses') or []) if isinstance(h, dict)]
    return result
