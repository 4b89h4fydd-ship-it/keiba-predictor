"""Bridge only the existing, explicitly configured SmartRc feed's pedigree facts.

No public-page scraper and no SmartRc ratings/tempo model are enabled here.
The configured feed must be covered by the operator's data-use permissions.
"""
from copy import deepcopy
from arvexq.databanks.registry import DataSource, SourceCapabilities
from arvexq.ingest.horse_identity import _horse_key


def pedigree_rows(fetch, race, *, configured):
    if not configured:
        return []
    response = fetch(race)
    if not isinstance(response, dict) or response.get("status") != "done":
        return []
    return [{"horseNumber": row.get("horseNumber"), "name": row.get("name"),
             "pedigree": deepcopy(row["pedigree"])}
            for row in response.get("rows", []) if isinstance(row, dict)
            and isinstance(row.get("pedigree"), dict) and row["pedigree"]]


def build_smartrc_source(fetch, *, configured):
    if not configured or not callable(fetch):
        return None
    def pedigree(horse, race, limit=5):
        # Both observations must match. A contradictory name at the same saddle
        # number must never assign one horse's ancestry to another horse.
        name = _horse_key(horse.get("name"))
        number = str(horse.get("horseNumber") or "")
        rows = [row for row in pedigree_rows(fetch, race, configured=True)
                if name and number and _horse_key(row.get("name")) == name
                and str(row.get("horseNumber") or "") == number]
        return {"pedigree": rows[0]["pedigree"]} if len(rows) == 1 else {}
    return DataSource("smartrc_pedigree", "both", 30,
                      SourceCapabilities(pedigree=True), {"pedigree": pedigree})
