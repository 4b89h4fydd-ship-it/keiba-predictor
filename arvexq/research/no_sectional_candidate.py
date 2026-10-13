"""Research-only zero-sectional candidate: distinct recent form and condition evidence."""
from arvexq.prediction.past_performance import observed_runs

def score(horse,race):
    runs=observed_runs(horse,race,limit=5)
    if not runs:return None
    quality=[(x["fieldSize"]-x["finish"])/(x["fieldSize"]-1) for x in runs]
    weights=[5-i for i in range(len(quality))]
    form=sum(w*q for w,q in zip(weights,quality))/sum(weights)
    dist=race.get("distance")
    surface=race.get("surface")
    comparable=[]
    for run,q in zip(runs,quality):
        try:
            match=dist is not None and run.get("distance") is not None and abs(float(run["distance"])-float(dist))<=150
        except (ValueError,TypeError):
            match=False
        if match and surface and run.get("surface")==surface:comparable.append(q)
    if comparable:
        # Shrink sparse condition evidence rather than treating it as five starts.
        condition=sum(comparable)/len(comparable)
        strength=min(0.25,0.08*len(comparable))
        return (1-strength)*form+strength*condition
    return form
