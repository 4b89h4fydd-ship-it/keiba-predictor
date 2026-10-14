"""Research-only observable position proxy; NOT the full Mineta 50/30/20 model."""
from arvexq.prediction.past_performance import observed_runs

def position_proxy(horse, race):
    runs=observed_runs(horse, race, limit=5)
    values=[]
    for run in runs:
        corners=run.get("cornerPositions")
        field=run.get("fieldSize")
        if not isinstance(corners,list) or not corners:
            continue
        try:
            first=float(corners[0]);last=float(corners[-1]);field=float(field)
        except (ValueError,TypeError):continue
        if not (field>1 and 1<=first<=field and 1<=last<=field):continue
        # Front position dominates; avoiding a major fade receives modest credit.
        front=(field-first)/(field-1)
        maintenance=1-max(0,last-first)/(field-1)
        values.append(.75*front+.25*maintenance)
    if not values:return None
    return sum((len(values)-i)*v for i,v in enumerate(values))/sum(range(1,len(values)+1))
