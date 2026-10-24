"""Six independent shadow stages from saved observations through candidate bets."""
from copy import deepcopy
from arvexq.research.stage63.ability import prior_runs, score_field
from arvexq.research.stage63.running_style import style_field
from arvexq.research.stage63.probability import distribution
from .circuits import CONFIGS, circuit, discipline, active as is_active
from .marks import roles
from .tickets import select

STAGES=("ability","runningStyle","pace","probability","marks","tickets")


def predict(race, *, expected_circuit, ability_method=None):
    owner=circuit(race)
    if owner!=expected_circuit:
        raise ValueError("cross-circuit execution")
    config=deepcopy(CONFIGS[owner])
    method=ability_method or config["ability"]
    stages={k:{"status":"blocked","value":None} for k in STAGES}
    result={"raceId":race["id"],"date":race["date"],"circuit":owner,
            "modelVersion":config["version"],"abilityMethod":method,
            "stages":stages,"independent":False,"productionEligible":False,
            "blockers":[]}
    if discipline(race)!="flat":
        result["blockers"].append({"reason":"unsupported-discipline","discipline":discipline(race)})
        return result
    horses=race.get("horses")
    if not isinstance(horses,list) or type(race.get("fieldSize")) is not int or race["fieldSize"]!=len(horses):
        raise ValueError("saved full roster/fieldSize mismatch")
    if any(not isinstance(h,dict) for h in horses):
        raise ValueError("invalid horse row")
    numbers=[h.get("horseNumber") for h in horses]
    if any(type(n) is not int or n<=0 for n in numbers) or len(set(numbers))!=len(numbers):
        raise ValueError("ambiguous horse numbers")
    active=[h for h in horses if is_active(h)]
    if len(active)<3:
        result["blockers"].append({"reason":"fewer-than-three-active-runners"})
        return result
    histories={}
    for h in active:
        no=h["horseNumber"]
        try:
            runs=prior_runs(h,race["date"])
        except ValueError:
            result["blockers"].append({"horseNumber":no,"reason":"conflicting-history"})
            runs=[]
        usable=[]
        for run in runs:
            # Banei position/finish cannot silently become a flat-racing feature.
            if discipline(run)!=discipline(race):
                result["blockers"].append({"horseNumber":no,"reason":"incompatible-history-discipline","date":run.get("date")})
            else:
                usable.append(run)
        histories[no]=usable
    ability=score_field(histories,method)
    style=style_field(histories,config["styleWindow"])
    stages["ability"]={"status":"research-only" if all(v is not None for v in ability.values()) else "incomplete",
                       "value":ability}
    stages["runningStyle"]={"status":"research-only" if all(v is not None for v in style.values()) else "incomplete",
                            "value":style}
    for no in histories:
        if ability[no] is None:
            result["blockers"].append({"horseNumber":no,"reason":"no-valid-finish-history","rawRuns":len(next(h for h in active if h["horseNumber"]==no).get("recentRaces") or [])})
        if style[no] is None:
            result["blockers"].append({"horseNumber":no,"reason":"no-valid-corner-history"})
    # Conservative full-field evidence gate remains shared by all candidates.
    if any(v is None for v in ability.values()) or any(v is None for v in style.values()):
        return result
    # First-corner quartiles describe observed positioning, NOT which runner
    # will take the lead today.  The previous fixed tactical boosts invented
    # pace outcomes and displaced high-ability winners from product marks.
    # Keep the six stages, but withhold unsupported race-pace adjustments
    # until actual pace/lead evidence can be evaluated without leakage.
    positions = ("前方", "好位", "中団", "後方")
    profiles = {}
    for no, shares in style.items():
        peak = max(shares)
        dominant = [i for i, value in enumerate(shares) if value == peak]
        profiles[no] = positions[dominant[0]] if len(dominant) == 1 else "位置取り混在"
    front_observed = sorted(
        style, key=lambda no: (-(style[no][0] + style[no][1]), no)
    )
    deltas = [{no: 0.0 for no in ability}]
    result["paceEvidence"] = {
        "source": "preoff-prior-first-corner-observations",
        "observedPositionProfiles": profiles,
        "earlyPositionObservedOrder": front_observed,
        "actualLeadVerified": False,
        "actualPaceVerified": False,
        "uncertainty": "初角の前方傾向だけでは逃げ主張・先行争い・控える馬を判定できない",
        "scenarioOccurrenceCalibrated": False,
        "otherExpertFeaturesVerified": False,
        "aiEnsembleTrained": False,
    }
    stages["pace"] = {
        "status": "observed-position-only-pace-unverified",
        "value": deltas, "scenarioWeightsVerified": False,
        "model": "no-unsupported-tactical-boost",
    }
    # The six stages are one causal chain. Keep expert corroboration separate
    # until track/pedigree/training evidence is verified and backtested.
    probs=distribution(ability,deltas,config["temperature"])
    podium={no:sum(p for combo,p in probs["trifecta"].items() if no in combo)
            for no in ability}
    trifecta=[{"combo":list(combo),"probability":prob}
              for combo,prob in sorted(probs["trifecta"].items())]
    stages["probability"]={"status":"research-only-uncalibrated",
                          "value":{"win":probs["win"],"top3":podium,
                                   "trifecta":trifecta},
                          "trifectaMass":sum(probs["trifecta"].values()),
                          "calibrationVerified":False}
    stages["marks"]={"status":"research-only-unvalidated","value":roles(probs["win"],podium)}
    stages["tickets"]={"status":"research-only-unvalidated","value":select(probs)}
    return result
