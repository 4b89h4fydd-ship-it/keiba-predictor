"""Provider row composition. Field policies can be replaced independently."""
from arvexq.components.item_025.module_reference_horse_number import original as horse_number
from arvexq.components.item_026.module_reference_frame_number import original as frame_number
from arvexq.components.item_027.module_reference_name import original as name
from arvexq.components.item_028.module_reference_sex import original as sex
from arvexq.components.item_029.module_reference_age import original as age
from arvexq.components.item_030.module_reference_carried_weight import original as carried_weight
from arvexq.components.item_031.module_reference_jockey import original as jockey
from arvexq.components.item_032.module_reference_trainer import original as trainer
from arvexq.components.item_033.module_reference_affiliation import original as affiliation
from arvexq.components.item_034.module_reference_body_weight import original as body_weight
from arvexq.components.item_035.module_reference_body_weight_change import original as body_weight_change
from arvexq.components.item_059.module_reference_win_odds import original as win_odds
from arvexq.components.item_061.module_reference_popularity import original as popularity
from . import status
from .dom import horse_info

FIELDS = {"name": name.extract, "sex": sex.extract, "age": age.extract,
          "carriedWeight": carried_weight.extract, "jockey": jockey.extract, "affiliation": affiliation.extract,
          "trainer": trainer.extract, "bodyWeight": body_weight.extract,
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
    result.update({"horseNumber": number, "frameNumber": frame_number.extract(row),
                   "name": horse_name, "scratched": bool(result["status"]), "recentRaces": [],
                   "jockeyStats": {}, "trainerStats": {}, "jockeyProfile": {}, "trainerProfile": {},
                   "source": "netkeiba"})
    return result
