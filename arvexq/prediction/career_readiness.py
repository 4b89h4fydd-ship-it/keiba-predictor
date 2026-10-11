from __future__ import annotations
from typing import Any
from arvexq.career_missing import build_career_analysis
from arvexq.pipeline.fingerprints import active_horses

READINESS_VERSION = "arvexq-career-readiness-v1"
_READY_STATES = {"complete", "complete-no-starts", "complete-with-missing-fields"}

def assess_career_readiness(detail: dict[str, Any] | None) -> dict[str, Any]:
    race = detail if isinstance(detail, dict) else {}
    horses = active_horses(race)
    # 新馬 is an entry-restricted debut class: a runner with genuinely zero
    # eligible earlier starts needs no fabricated lifetime performances.
    # Do not apply this exception to 障害, 未勝利 or other older runners.
    title = str(race.get("title") or race.get("raceName") or "")
    debut_class = "新馬" in title or str(race.get("analysisMode") or "") == "新馬"
    blocked, complete, debut_proven = [], 0, 0
    for horse in horses:
        analysis = build_career_analysis(horse, race)
        evidence = analysis.get("acquisition_evidence") or {}
        verified = bool(analysis.get("career_complete") and analysis.get("career_state") in _READY_STATES)
        # An actual observed past start contradicts debut-only eligibility.
        debut_zero = bool(debut_class and analysis.get("career_state") == "no-history"
                          and int(evidence.get("currentEligibleRuns") or 0) == 0)
        if verified or debut_zero:
            complete += 1
            debut_proven += int(debut_zero and not verified)
        else:
            blocked.append({"horseNumber": int(horse.get("horseNumber") or 0), "name": str(horse.get("name") or ""), "state": str(analysis.get("career_state") or "unverified"), "reason": str(evidence.get("reason") or "full-career-unverified"), "reportedStarts": evidence.get("reportedStarts"), "observedRuns": int(evidence.get("currentEligibleRuns") or 0)})
    total = len(horses)
    ready = bool(total >= 2 and complete == total)
    return {"version": READINESS_VERSION, "ready": ready, "status": "ready" if ready else ("fetching" if total else "unavailable"), "activeHorses": total, "completeHorses": complete, "debutClassNoStarts": debut_proven, "blockedHorses": blocked}

def attach_career_readiness(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(detail, dict): return detail
    readiness = assess_career_readiness(detail)
    detail["careerReadiness"] = readiness
    pm = detail.setdefault("preparedMeta", {})
    pm.update({"careerReady": readiness["ready"], "careerCompleteHorses": readiness["completeHorses"], "careerActiveHorses": readiness["activeHorses"]})
    return detail
