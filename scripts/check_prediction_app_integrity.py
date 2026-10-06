#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "arvexq/ui/static/app.js").read_text(encoding="utf-8")
build = (ROOT / "build_static.py").read_text(encoding="utf-8")
final_marks = (ROOT / "arvexq/prediction/final_marks.py").read_text(encoding="utf-8")
multi_head = (ROOT / "arvexq/prediction/multi_head.py").read_text(encoding="utf-8")
race_analysis = (ROOT / "arvexq/services/race_analysis.py").read_text(encoding="utf-8")
remove_value = (ROOT / "scripts/arvexq_remove_value_races.py").read_text(encoding="utf-8")
selection_policy = (ROOT / "scripts/arvexq_enforce_selection_policy.py").read_text(encoding="utf-8")
special_patch = (ROOT / "scripts/arvexq_patch_special_races.py").read_text(encoding="utf-8")

checks = {
    "one-source-assignPredictionMarks": js.count("function assignPredictionMarks(") == 1,
    "authoritative-mark-guard": "function applyServerAuthoritativeMarks(rows,r)" in js,
    "predict-applies-server-marks": "assignPredictionMarks(rows,modelRace);applyServerAuthoritativeMarks(rows,modelRace);" in js,
    "static-build-no-prediction-override": "ABILITY_FIRST_JS" not in build and "_inject_before_iife_close" not in build and "assignPredictionMarks=function" not in build,
    "race-cache-build-namespaced": 'String(window.ARVEXQ_BUILD||"dev")+":races:"' in js,
    "detail-cache-build-namespaced": 'String(window.ARVEXQ_BUILD||"dev")+":detail:"' in js,
    "bundle-cache-build-namespaced": 'String(window.ARVEXQ_BUILD||"dev")+":fullbundle:"' in js,
    "live-detail-ttl-bounded": "age>2*60000" in js,
    "bodyweight-invalidates-prediction": "predictionInputChanged" in js and "delete state.race._prediction" in js,
    "strict-selection-market-independent": "!mh.dangerPopular" not in js,
    "strict-selection-authoritative-agreement": "authAgree=!authAxisNo||leaderNo===authAxisNo" in js and "mhAgree=authAgree&&" in js,
    "featured-uses-strict-selector": "try{sel=strictSelectedRaceProfile(r,p)}catch(e){}" in js,
    "featured-includes-main": "isMainForecastRace(r)||raceIsGraded(r)" in js,
    "main-forecast-helper": "function isMainForecastRace(r){" in js,
    "main-fallback-is-last-race": "return rows[rows.length-1]" in js,
    "old-main-second-last-fallback-gone": "return rows.length>=2?rows[rows.length-2]:rows[rows.length-1]" not in js,
    "special-scope-main-graded-kochi": all(x in js for x in ("function specialForecastRaceCandidates(){", "add(mainRaceForTrack(groups[k]))", "add(kochiFinalRace(rows))")),
    "special-prebuild-enabled": "function prebuildSpecialForecastPlans(){" in js and "prebuildSpecialForecastPlans();" in js,
    "stored-bet-view-immutable": "function immutableStoredAiBetView(r,plan){" in js and "if(stored)return immutableStoredAiBetView(r,stored);" in js,
    "locked-bet-scratch-safety": "発走前固定後に取消・除外馬が発生" in js,
    "locked-bet-cancel-safety": "レース中止・取止めのため" in js,
    "stored-plan-not-recomputed-prepost": "if(terminal&&stored)return stored;" not in js,
    "bet-lock-state-visible": "暫定・更新あり" in js and "発走前固定" in js,
    "premature-lock-bodyweight-guard": "remain>45&&!bodyReady" in js,
    "bet-axis-needs-authoritative-agreement": "axisLocked=axisStable&&axisAgreement&&axisConfidence" in js,
    "core-mark-engine-four-pillar": 'MARK_ENGINE_VERSION = "arvexq-four-pillar-marks-v4"' in final_marks,
    "multihead-v2": 'MODEL_VERSION = "arvexq-multi-head-v2"' in multi_head,
    "multihead-upside-market-independent": "setup_lift = strength_rank - win_rank" in multi_head and "popularity >= 5" not in multi_head,
    "mass-ml-not-in-production-mark-path": "mass_model_runtime" not in final_marks and "mass_model_runtime" not in race_analysis,
    "pwa-prev-build-compat": all(v in build for v in ('"v323"', '"v322"')),
    "version-label-authoritative": '"shell":"four-pillar-authoritative"' in build,
    "value-cleanup-does-not-own-special-scope": "SPECIAL =" not in remove_value and "v325" not in remove_value and "special forecast source unexpectedly missing" in remove_value,
    "selection-policy-preserves-main-featured": "isMainForecastRace(r)||raceIsGraded(r)" in selection_policy,
    "special-patch-owns-lock-safety": "immutableStoredAiBetView" in special_patch and "remain>45&&!bodyReady" in special_patch,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("OK  " if ok else "FAIL"), name)
if failed:
    raise SystemExit("prediction/app integrity failed: " + ", ".join(failed))
print("prediction-app-integrity-ok", len(checks))
