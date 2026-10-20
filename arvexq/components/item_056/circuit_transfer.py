"""Independent factual JRA/NAR race affiliation and transfer evidence (requirement 56).

Never infer the affiliation of an unknown track, and never use future outcomes.
This module does not generate probabilities, predictions, marks or tickets.
"""
JRA_TRACKS = frozenset(("札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"))
NAR_TRACKS = frozenset(("門別","帯広","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"))

def race_circuit(run):
    if not isinstance(run,dict): return None
    explicit=str(run.get("circuit") or run.get("organization") or "").strip().lower()
    if explicit in ("中央","jra","central"): return "JRA"
    if explicit in ("地方","nar","local"): return "NAR"
    track=str(run.get("track") or "").strip()
    if track in JRA_TRACKS: return "JRA"
    if track in NAR_TRACKS: return "NAR"
    return None

def transfer_observations(horse,target):
    """Classify reported starts in their supplied order; cannot assert undocumented moves."""
    runs=(horse or {}).get("allPastRuns") or (horse or {}).get("recentRaces") or []
    observed=[race_circuit(r) for r in runs if isinstance(r,dict)]
    known=[x for x in observed if x in ("JRA","NAR")]
    return {"targetCircuit":race_circuit(target),
            "knownCircuitStarts":len(known),
            "unknownCircuitStarts":len(observed)-len(known),
            "hasCrossCircuitHistory":len(set(known))>1,
            "latestReportedCircuit":known[0] if known else None}
