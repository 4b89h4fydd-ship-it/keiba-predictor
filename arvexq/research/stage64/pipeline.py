"""Six independent shadow stages from saved observations through candidate bets."""
from copy import deepcopy
from math import isfinite, nextafter, inf
from arvexq.research.stage63.ability import prior_runs, score_field, quality
from arvexq.research.stage63.running_style import style_field
from arvexq.research.stage63.probability import distribution
from .circuits import CONFIGS, circuit, discipline, active as is_active
from .marks import roles
from .tickets import select
from .holistic import evidence as holistic_evidence, direct_rematch_candidate

STAGES=("ability","runningStyle","pace","probability","marks","tickets")


def _same_track_distance_evidence(horse, race):
    """Read-only historical facts, never a weighted tactical adjustment.

    Prefer the recorded full career when present, but leave Stage64 ability
    calculation unchanged until a separately evaluated model decision.
    Strict historical date cutoff prevents today/future-result leakage.
    """
    source = horse.get("allPastRuns") or horse.get("recentRaces") or []
    if not isinstance(source, list):
        return {"status": "history-unavailable", "observedStarts": 0,
                "sameTrackDistanceStarts": None, "sameTrackDistanceWins": None,
                "sameTrackDistanceTop3": None}
    try:
        runs = prior_runs({"recentRaces": source}, race["date"])
    except ValueError:
        return {"status": "conflicting-history", "observedStarts": 0,
                "sameTrackDistanceStarts": None, "sameTrackDistanceWins": None,
                "sameTrackDistanceTop3": None}
    target_track = str(race.get("track") or "").strip()
    target_distance = race.get("distance")
    try:
        target_distance = float(target_distance) if target_distance is not None else None
    except (TypeError, ValueError):
        target_distance = None
    if not target_track or target_distance is None or not target_distance > 0:
        return {"status": "context-unavailable", "observedStarts": len(runs),
                "sameTrackDistanceStarts": None, "sameTrackDistanceWins": None,
                "sameTrackDistanceTop3": None}
    comparable = []
    eligible = [r for r in runs if quality(r) is not None
                and discipline(r) == discipline(race)]
    if target_track and target_distance is not None and target_distance > 0:
        for r in eligible:
            if str(r.get("track") or "").strip() != target_track:
                continue
            try:
                distance = float(r.get("distance"))
            except (TypeError, ValueError):
                continue
            if distance == target_distance:
                comparable.append(r)
    return {"status": "observed-not-predictive", "observedStarts": len(eligible),
            "sameTrackDistanceStarts": len(comparable),
            "sameTrackDistanceWins": sum(r["finish"] == 1 for r in comparable),
            "sameTrackDistanceTop3": sum(r["finish"] <= 3 for r in comparable),
            "source": "existing-past-runs-strictly-before-race"}


def _public_position_tactics(race, histories):
    """Observable components of publicly described pace analysis.

    These are facts/flags, NOT an estimate of today's actual leader, nor an
    implementation of a forecaster's undisclosed judgement. Do not feed flags
    into a fabricated ability delta or probability without forward validation.
    """
    distance = race.get("distance")
    try:
        distance = float(distance) if distance is not None else None
    except (TypeError, ValueError):
        distance = None
    profiles = {}
    high_intent = []
    unknown = []
    shortened = []
    extended = []
    for no in sorted(histories):
        runs = histories[no]
        if not runs:
            profiles[no] = {"status": "no-prior-run", "lastRunDate": None,
                            "top3PositionObserved": None, "distanceChange": "unknown"}
            unknown.append(no)
            continue
        run = runs[0]
        positions = run.get("cornerPositions") or run.get("passing") or []
        field_size = run.get("fieldSize")
        observed = type(field_size) is int and field_size >= 3 and isinstance(
            positions, list) and bool(positions) and all(
            type(p) in (int, float) and isfinite(p) and 1 <= p <= field_size
            for p in positions
        )
        top3 = any(p <= 3 for p in positions) if observed else None
        old_distance = run.get("distance")
        try:
            old_distance = float(old_distance) if old_distance is not None else None
        except (TypeError, ValueError):
            old_distance = None
        change = "unknown"
        if distance is not None and old_distance is not None and distance > 0 and old_distance > 0:
            if distance > old_distance:
                change = "extension"
                extended.append(no)
            elif distance < old_distance:
                change = "shortening"
                shortened.append(no)
            else:
                change = "unchanged"
        if top3 is None:
            unknown.append(no)
        # His published first-pass criterion includes previous top-three
        # positions and the possibility that distance extension increases
        # forward intent. Neither proves an actual lead today.
        flagged = top3 is True or change == "extension"
        if flagged:
            high_intent.append(no)
        profiles[no] = {
            "status": "prior-observation" if top3 is not None else "prior-position-missing",
            "lastRunDate": run.get("_raceDate") or run.get("date"),
            "lastRunDistance": old_distance,
            "top3PositionObserved": top3,
            "distanceChange": change,
            "forwardIntentCandidate": flagged,
        }
    # Horse number represents starting position along the gate. Frame number
    # is NOT interchangeable with individual horse numbers.
    adjacent = [[a, b] for a, b in zip(high_intent, high_intent[1:]) if b - a == 1]
    adjacent_members = {no for pair in adjacent for no in pair}
    separated = [no for no in high_intent if no not in adjacent_members]
    return {
        "source": "preoff-latest-prior-run-and-entered-horse-numbers",
        "methods": ["prior-top-three-at-any-corner", "distance-extension-flag",
                    "horse-number-adjacency"],
        "observedProfiles": profiles,
        "forwardIntentCandidates": high_intent,
        "adjacentForwardIntentPairs": adjacent,
        "separatedForwardIntentCandidates": separated,
        "distanceShorteningCandidates": shortened,
        "distanceExtensionCandidates": extended,
        "positionUnknown": unknown,
        "pacePredicted": False,
        "actualLeadVerified": False,
        "actualCompetitionVerified": False,
    }


def _prior_career_for_nar(horse, cutoff):
    """Re-use the existing saved career, never download or synthesize starts.

    JRA keeps its separately registered input policy. Accept a longer NAR
    history only if every visible recent start is represented with consistent
    identity and finish. An incomplete archive cannot silently replace the
    known observations. All runs must be strictly earlier than race day.
    """
    recent = prior_runs(horse, cutoff)
    raw_full = horse.get("allPastRuns")
    transport = horse.get("careerTransport")
    claimed = transport.get("observedRuns") if isinstance(transport, dict) else None
    # The pre-existing lossless archive is the authoritative recovery path
    # only when the visible whole-career lane is absent or incomplete.
    needs_recover = not isinstance(raw_full, list) or not raw_full or (
        type(claimed) is int and len(raw_full) < claimed)
    if needs_recover and isinstance(horse.get("careerArchive"), dict):
        from arvexq.ingest.career_transport import recover_horse
        try:
            raw_full = recover_horse(horse, cutoff).get("allPastRuns")
        except (ValueError, KeyError, TypeError, OSError):
            return recent, False
    if not isinstance(raw_full, list) or not raw_full:
        return recent, False
    full = prior_runs({"recentRaces": raw_full}, cutoff)
    if len(full) <= len(recent):
        return recent, False
    claims = horse.get("careerTransport")
    if isinstance(claims, dict) and claims.get("observedRuns") is not None:
        claimed = claims["observedRuns"]
        if type(claimed) is not int or claimed > len(full):
            return recent, False
    by_day = {r.get("_raceDate") or r.get("date"): r for r in full}
    for run in recent:
        day = run.get("_raceDate") or run.get("date")
        stored = by_day.get(day)
        if stored is None:
            return recent, False
        for key in ("track", "raceNumber", "finish", "fieldSize"):
            old, new = run.get(key), stored.get(key)
            if old is not None and new is not None and old != new:
                return recent, False
    return full, True


def _jra_historical_observations(horse, cutoff):
    """JRA winner assessment: observed recent starts, not the NAR archive policy."""
    return prior_runs(horse, cutoff), False


def _nar_historical_observations(horse, cutoff):
    """NAR winner assessment: validated saved career before race date."""
    return _prior_career_for_nar(horse, cutoff)


OBSERVATION_POLICIES = {
    "jra": ("jra-visible-history", _jra_historical_observations),
    "nar": ("nar-lossless-observed-career", _nar_historical_observations),
}


def predict(race, *, expected_circuit, ability_method=None):
    owner=circuit(race)
    if owner!=expected_circuit:
        raise ValueError("cross-circuit execution")
    config=deepcopy(CONFIGS[owner])
    policy_id, history_reader = OBSERVATION_POLICIES[owner]
    if config["abilityObservationPolicy"] != policy_id:
        raise ValueError("cross-circuit ability method conflict")
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
    expanded_careers = []
    for h in active:
        no=h["horseNumber"]
        try:
            runs, expanded = history_reader(h, race["date"])
            if expanded:
                expanded_careers.append(no)
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
    result["predictionMethod"] = {
        "circuit": owner,
        "abilityHistory": policy_id,
        "winnerReview": config["winnerReviewPolicy"],
        "sixStageChainPreserved": True,
        "unvalidatedTacticalBoostsApplied": False,
    }
    result["abilityHistoryCoverage"] = {
        "source": "existing-saved-allPastRuns-when-compatible" if owner == "nar"
                  else "existing-jra-recentRaces",
        "fullCareerUsedHorseNumbers": sorted(expanded_careers),
        "fullCareerRunners": len(expanded_careers),
        "activeRunners": len(active),
        "fullCareerCoverageVerified": False,
        "missingCareerDoesNotMeanPoorAbility": True,
    }
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
        "historicalCourseEvidence": {h["horseNumber"]: _same_track_distance_evidence(h, race)
                                     for h in active},
        "publicPositionTactics": _public_position_tactics(race, histories),
        "observedPositionProfiles": profiles,
        "earlyPositionObservedOrder": front_observed,
        "actualLeadVerified": False,
        "actualPaceVerified": False,
        "uncertainty": "初角の前方傾向だけでは逃げ主張・先行争い・控える馬を判定できない",
        "scenarioOccurrenceCalibrated": False,
        "otherExpertFeaturesVerified": False,
        "aiEnsembleTrained": False,
    }
    # Use the existing lossless full-career lane for historical comparison
    # where it genuinely contains the current recent-run cohort. Avoid
    # replacing newer observed runs with an incomplete older archive.
    holistic_histories = dict(histories)
    for horse in active:
        no = horse["horseNumber"]
        archived = horse.get("allPastRuns")
        if not isinstance(archived, list) or not archived:
            continue
        try:
            extended = prior_runs({"recentRaces": archived}, race["date"])
        except ValueError:
            continue
        if not all(discipline(run) == discipline(race) for run in extended):
            continue
        def prior_identity(run):
            return (run.get("_raceDate") or run.get("date"),
                    run.get("track"), run.get("raceNumber"))
        extended_ids = {prior_identity(run) for run in extended}
        if extended and all(prior_identity(run) in extended_ids for run in histories[no]):
            holistic_histories[no] = extended
    result["paceEvidence"]["holisticWinnerEvidence"] = holistic_evidence(
        race, holistic_histories, active)
    # Replace the NAR winner ordering only when the already registered direct-
    # rival review finds an uncontradicted, corroborated historical rematch.
    # This stays inside the six existing stages: the same revised ability
    # ordering feeds win probability, marks and tickets, with no extra route.
    review = config["winnerReviewPolicy"]
    original_order = sorted(ability, key=lambda no: (-ability[no], no))
    rival = None
    applied = False
    if owner == "nar":
        if review != "nar-full-career-direct-rival-review":
            raise ValueError("cross-circuit winner review conflict")
        rival = direct_rematch_candidate(
            original_order, result["paceEvidence"]["holisticWinnerEvidence"])
        if rival is not None:
            chosen, original = rival["horseNumber"], rival["otherHorseNumber"]
            if original == original_order[0] and chosen in original_order[1:5]:
                ability[chosen], ability[original] = ability[original], ability[chosen]
                # Resolve an exact finish-quality tie without guessing a
                # performance boost or fabricating a win probability.
                if sorted(ability, key=lambda no: (-ability[no], no))[0] != chosen:
                    ability[chosen] = nextafter(max(ability.values()), inf)
                applied = True
    elif owner == "jra":
        if review != "jra-course-distance-opposition-review":
            raise ValueError("cross-circuit winner review conflict")
    else:
        raise ValueError("unsupported prediction circuit")
    result["winnerEvidenceComparison"] = {
        "method": review,
        "proposedHeadToHeadResearchChallenger": rival,
        "selectionPolicy": ("corroborated-nar-direct-rematch-applied"
                            if applied else "original-ability-ranking"),
        "winnerRankUnchanged": not applied,
        "appliedToWinProbabilityAndMarks": applied,
        "originalWinnerHorseNumber": original_order[0],
        "selectedWinnerHorseNumber": (rival["horseNumber"]
                                      if applied else original_order[0]),
        "forwardAccuracyValidated": False,
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
