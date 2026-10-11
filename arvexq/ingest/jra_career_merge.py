"""Keep all authenticated JRA profile starts with a five-run UI projection."""
from __future__ import annotations
import copy
from typing import Any
from arvexq.ingest.full_career import merge_career


def merge_full_profile_history(horse:dict[str,Any], official_runs:list[dict[str,Any]],
                               cutoff:str)->dict[str,Any]:
    """Merge all available pre-race starts; no fabricated completeness assertion."""
    out=copy.deepcopy(horse)
    previous=[*(out.get("allPastRuns") or []),*(out.get("recentRaces") or [])]
    full=merge_career(previous,official_runs,cutoff)
    if full:
        out["allPastRuns"]=full
        out["recentRaces"]=full[:5]
    return out
