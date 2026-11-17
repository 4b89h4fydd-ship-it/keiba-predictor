"""Research-only field-aware position model, not Mineta's official 50/30/20."""
from arvexq.prediction.past_performance import observed_runs

def _n(x):
    try:return float(x)
    except (ValueError,TypeError):return None

def score_race(horses,race):
    measurements={}
    for h in horses:
        no=int(h.get("horseNumber") or 0)
        if not no:continue
        runs=observed_runs(h,race,limit=5)
        if not runs:continue
        first=runs[0]
        corners=first.get("cornerPositions")
        field=_n(first.get("fieldSize"))
        if not isinstance(corners,list) or not corners or not field or field<=1:continue
        c=_n(corners[0])
        if c is None or not 1<=c<=field:continue
        recent=[]
        for run in runs:
            pos=run.get("cornerPositions")
            fieldsize=_n(run.get("fieldSize"))
            if isinstance(pos,list) and pos and fieldsize and fieldsize>1:
                p=_n(pos[0])
                if p is not None and 1<=p<=fieldsize:
                    recent.append((fieldsize-p)/(fieldsize-1))
        if not recent:continue
        measurements[no]={"front":sum(recent)/len(recent),
                          "previousFront":c<=3,
                          "frame":_n(h.get("frameNumber") or h.get("horseNumber"))}
    if len(measurements)<2:return {}
    share=sum(x["previousFront"] for x in measurements.values())/len(measurements)
    out={}
    for no,m in measurements.items():
        others=[v for n,v in measurements.items() if n!=no and v["frame"] is not None]
        outer=sum(v["front"]>m["front"] and v["frame"]>m["frame"] for v in others) if m["frame"] is not None else 0
        # Conservative: observable occupancy and surrounding threats only;
        # never claim measured first-turn distance, pace or time margin.
        positioning=m["front"]*(1-.20*share)
        clean_path=1/(1+outer) if m["frame"] is not None else None
        if clean_path is None:continue
        out[no]=.75*positioning+.25*clean_path
    return out
