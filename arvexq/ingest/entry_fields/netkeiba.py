"""Provider row composition. Field policies can be replaced independently."""
from . import horse_number, frame_number, name, sex, age, carried_weight, jockey, trainer, body_weight, body_weight_change, win_odds, popularity, status, affiliation
from .dom import horse_info

FIELDS = {"name": name.extract, "sex": sex.extract, "age": age.extract,
          "carriedWeight": carried_weight.extract, "jockey": jockey.extract,
          "trainer": trainer.extract, "affiliation": affiliation.extract, "bodyWeight": body_weight.extract,
          "bodyWeightChange": body_weight_change.extract, "winOdds": win_odds.extract,
          "popularity": popularity.extract, "status": status.extract}

def parse_row(row, index=None, *, extractors=None):
    """DOM row -> compatible runner dict or None. Inject individual field adapters."""
    if horse_info(row) is None: return None
    adapters = dict(FIELDS)
    if extractors is not None: adapters.update(extractors)
    horse_name = adapters["name"](row)
    number = horse_number.extract(row, index)
    if not horse_name or number <= 0: return None
    result = {key: adapter(row) for key, adapter in adapters.items() if key != "name"}
    result.update({"horseNumber": number, "frameNumber": frame_number.extract(row) or int((number + 1) // 2),
                   "name": horse_name, "scratched": bool(result["status"]), "recentRaces": [],
                   "jockeyStats": {}, "trainerStats": {}, "jockeyProfile": {}, "trainerProfile": {},
                   "source": "netkeiba"})
    return result
