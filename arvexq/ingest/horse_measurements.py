"""Independent horse-body and carried-weight validation for race ingestion."""
from arvexq.ingest.entry_fields.body_weight_change import normalize as normalize_body_weight_change

from arvexq.ingest.entry_fields.body_weight import _safe_body_weight_value


from arvexq.ingest.entry_fields.carried_weight import _safe_carried_weight_value


def _sanitize_horse_measurements(h:dict)->dict:
    if not isinstance(h,dict):return h
    z=dict(h)
    bw=_safe_body_weight_value(z.get("bodyWeight") or z.get("horseWeight") or z.get("currentBodyWeight"))
    z["bodyWeight"]=bw
    z["bodyWeightChange"]=normalize_body_weight_change(z.get("bodyWeightChange"))
    z["carriedWeight"]=_safe_carried_weight_value(z.get("carriedWeight"),bw)
    runs=[]
    for rr in list(z.get("allPastRuns") or z.get("recentRaces") or []):
        if not isinstance(rr,dict):continue
        q=dict(rr);rbw=_safe_body_weight_value(q.get("bodyWeight"));q["bodyWeight"]=rbw
        q["carriedWeight"]=_safe_carried_weight_value(q.get("carriedWeight"),rbw)
        runs.append(q)
    if z.get("allPastRuns") is not None:z["allPastRuns"]=runs
    z["recentRaces"]=runs[:5]
    return z


