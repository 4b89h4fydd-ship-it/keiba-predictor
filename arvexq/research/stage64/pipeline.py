"""Six independent shadow stages from saved observations through candidate bets."""
from copy import deepcopy
from math import isfinite
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
    # Replacement: Mineta-inspired positional race dynamics, not the old
    # independent four fixed pace adjustments. Data must be known pre-off.
    # Training weights/scenario occurrence rates have NOT been calibrated.
    positional = {no: tuple(vals) for no, vals in style.items()}
    front = {no: vals[0] + 0.5 * vals[1] for no, vals in positional.items()}
    pursuit = {no: vals[2] + vals[3] for no, vals in positional.items()}
    pressure = sum(front.values())
    competition = max(0.0, pressure - 1.0)
    # A contested lead affects all front-runners; late movers can benefit.
    neutral = {no: 0.0 for no in positional}
    contested = {no: 0.18 * competition * (pursuit[no] - front[no])
                 for no in positional}
    easy_lead = {no: 0.16 * front[no] / max(1.0, pressure)
                 - 0.08 * pursuit[no] for no in positional}
    closer_friendly = {no: 0.12 * pursuit[no] - 0.06 * front[no]
                       for no in positional}
    deltas = [neutral, contested, easy_lead, closer_friendly]
    result["paceEvidence"] = {
        "frontPressure": pressure,
        "frontCompetition": competition,
        "source": "preoff-prior-corner-positions",
        "scenarioOccurrenceCalibrated": False,
        "expertMethod": "mineta-public-position-and-pace-principles",
        "otherExpertFeaturesVerified": False,
        "aiEnsembleTrained": False,
    }
    stages["pace"]={"status":"research-hypotheses-not-calibrated","value":deltas,
                    "scenarioWeightsVerified":False,
                    "frontCompetition":competition,
                    "model":"mineta-position-competition-rewrite"}
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
