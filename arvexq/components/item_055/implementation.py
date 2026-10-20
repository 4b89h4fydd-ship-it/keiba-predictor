"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_merge_run_fields(base:dict,incoming:dict)->dict:
    """Merge duplicate starts field-by-field instead of discarding richer data."""
    out=dict(base or {})
    for key,value in (incoming or {}).items():
        if not _jra_run_value_present(key,out.get(key)) and _jra_run_value_present(key,value):out[key]=value
        elif key=="cornerPositions" and value and len(value)>len(out.get(key) or []):out[key]=value
    sources=[]
    for src in (str((base or {}).get("source") or ""),str((incoming or {}).get("source") or "")):
        if src and src not in sources:sources.append(src)
    if sources:out["source"]=" + ".join(sources)
    return out

def _jra_merge_runs(a:list[dict],b:list[dict],limit:int=5)->list[dict]:
    merged={};order=[]
    for r in list(a or [])+list(b or []):
        if not isinstance(r,dict):continue
        key=_jra_run_key(r)
        if key not in merged:
            merged[key]=dict(r);order.append(key)
        else:merged[key]=_jra_merge_run_fields(merged[key],r)
    allr=[merged[k] for k in order]
    allr.sort(key=lambda r:str(r.get("date") or ""),reverse=True)
    return allr[:limit]
