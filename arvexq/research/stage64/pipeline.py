"""Six independent shadow stages from saved observations through candidate bets."""
from copy import deepcopy
from arvexq.research.stage63.ability import prior_runs, score_field
from arvexq.research.stage63.running_style import style_field
from arvexq.research.stage63.pace import adjustments
from arvexq.research.stage63.probability import distribution
from .circuits import CONFIGS, circuit, discipline, active as is_active
from .marks import roles
from .tickets import select


def _qualitative_reading(histories, styles, horses):
    """Evidence-led race reading; never invent observations or expert opinions."""
    reading = {}
    for no, runs in histories.items():
        observed = [r for r in runs if isinstance(r.get("finish"), (int, float))
                    and isinstance(r.get("fieldSize"), int) and r["fieldSize"] >= r["finish"] >= 1]
        corners = [r for r in runs if (r.get("cornerPositions") or r.get("passing"))]
        recent = observed[0] if observed else None
        style = styles.get(no)
        if style is None:
            position = "不明"
        else:
            leading, stalking, midpack, closing = style
            maximum = max(style)
            position = ("逃げ", "先行", "差し", "追込")[style.index(maximum)] if maximum > 0 else "不明"
        # Multiple handicapping lenses use only existing observed history fields.
        # They are methodologies, NOT assertions of real forecasters' picks.
        course = [r for r in observed if r.get("track") == horse_track] if (horse_track := next(
            (h.get("track") for h in horses if h["horseNumber"] == no), None)) else []
        recent3 = observed[:3]
        direction = ("改善傾向" if len(recent3) >= 2 and recent3[0]["finish"] < recent3[-1]["finish"]
                     else "悪化傾向" if len(recent3) >= 2 and recent3[0]["finish"] > recent3[-1]["finish"]
                     else "横ばい・判断材料不足")
        methodology = {
            "回顧型": {"finding": direction, "evidenceRuns": len(recent3),
                      "limitation": "着順推移のみ。展開不利・映像は未評価"},
            "能力比較型": {"finding": "直近の相対着順を確認" if observed else "能力根拠不足",
                          "evidenceRuns": len(observed),
                          "limitation": "相手関係・レースレベル未確認"},
            "コース適性型": {"finding": "同コース過去走あり" if course else "同コース実績未確認",
                            "evidenceRuns": len(course),
                            "limitation": "競馬場名の一致のみで適性断定不可"},
            "展開型": {"finding": position, "evidenceRuns": len(corners),
                       "limitation": "過去の通過位置からの推定"},
        }
        reading[no] = {
            "horseNumber": no,
            "pastRunReading": {
                "latestFinish": recent.get("finish") if recent else None,
                "latestFieldSize": recent.get("fieldSize") if recent else None,
                "observedRuns": len(observed),
                "cornerEvidenceRuns": len(corners),
                "interpretation": "着順と通過位置を確認。映像・不利・相手レベルの検証は未取得"
                                  if observed else "着順根拠不足",
            },
            "predictedPosition": position,
            "positionEvidence": style,
            "methodologyFusion": methodology,
            "rivalRelationship": None,
            "advantageDisadvantage": [],
            "winningScenario": None,
            "unverified": ["他予想家の独立分析", "映像での不利", "騎手の戦術", "枠順との干渉"],
        }
    pressure = sum(1 for v in reading.values() if v["predictedPosition"] in ("逃げ", "先行"))
    leaders = [no for no, v in reading.items() if v["predictedPosition"] == "逃げ"]
    for no, v in reading.items():
        position = v["predictedPosition"]
        v["rivalRelationship"] = {
            "otherLeadingCandidates": [n for n in leaders if n != no],
            "forwardPressure": "競合候補あり" if pressure > 2 else "比較的少ない",
            "evidence": "出走馬の過去コーナー位置から推定。ゲート・枠順を踏まえた確定隊列ではない",
        }
        if position == "逃げ":
            v["advantageDisadvantage"].append("逃げ候補が単独" if len(leaders) == 1 else "逃げ候補が複数")
            v["winningScenario"] = "先手を確保して粘り込む展開"
        elif position == "先行":
            v["winningScenario"] = "好位を確保し直線で抜け出す展開"
        elif position in ("差し", "追込"):
            v["advantageDisadvantage"].append("前に行く馬が多い" if pressure > 2 else "前崩れの根拠は限定的")
            v["winningScenario"] = "先行勢が消耗し進路を確保できる展開"
        else:
            v["winningScenario"] = "通過位置の根拠不足で判定不可"
    return reading

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
    reading=_qualitative_reading(histories,style,active)
    result["raceReading"]={"approach":"展開主体・根拠明示","horses":reading,
                           "expertFusionStatus":"methodology-only-no-expert-picks",
                           "fusionPolicy":"展開を主体に回顧・能力・適性の根拠を並列確認。実在予想家の印は捏造しない"}
    stages["ability"]["raceReading"]={no: reading[no]["pastRunReading"] for no in reading}
    stages["runningStyle"]["positions"]={no: reading[no]["predictedPosition"] for no in reading}
    deltas=adjustments(style,config["pace"])
    # Select among the EXISTING tactical scenarios using opposing runners.
    # Do not fabricate outside experts or assign unvalidated scenario likelihoods.
    front=sum(style[n][0]+style[n][1] for n in style)
    leaders=sum(1 for n in reading if reading[n]["predictedPosition"]=="逃げ")
    if len(deltas)>1:
        if leaders==1 and front<=2:
            situation="単騎逃げ・先行負荷軽め"
            deltas=[deltas[0],deltas[2]]
        elif front>=3:
            situation="先行圧力高め"
            deltas=[deltas[0],deltas[1],deltas[3]]
        else:
            situation="隊列不確定・複数展開"
    else:
        situation="既存中央中立設定・展開補正未適用"
    result["raceReading"]["raceSituation"]=situation
    result["raceReading"]["scenarioSelection"]="出走馬の過去位置取りの相互関係で既存シナリオを選択"
    stages["pace"]={"status":"research-hypotheses-not-calibrated","value":deltas,
                    "scenarioWeightsVerified":False,"raceSituation":situation}
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
    stages["marks"]={"status":"research-only-unvalidated","value":roles(probs["win"],podium),
                     "reasoning":{no:{"position":reading[no]["predictedPosition"],
                                      "winScenario":reading[no]["winningScenario"],
                                      "advantageDisadvantage":reading[no]["advantageDisadvantage"]}
                                  for no in reading}}
    stages["tickets"]={"status":"research-only-unvalidated","value":select(probs),
                       "constructionRule":"展開別の既存3着内同時分布から券種横断で選定。オッズ未検証"}
    return result
