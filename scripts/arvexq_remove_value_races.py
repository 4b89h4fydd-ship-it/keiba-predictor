#!/usr/bin/env python3
from pathlib import Path
import runpy

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")


def remove_between(source: str, start: str, end: str) -> str:
    a = source.find(start)
    if a < 0:
        return source
    b = source.find(end, a + len(start))
    if b < 0:
        raise SystemExit(f"end marker not found for {start}")
    return source[:a] + source[b:]


# This pass has exactly one responsibility: remove the obsolete standalone
# expected-value race category. It must never rewrite special-forecast scope,
# prediction policy, build version, PWA shell, or bet-lock behavior.
text = remove_between(text, "function eliteValueRaceCut(rows){", "function expectedValueRaceCandidates(circuit){")
text = remove_between(text, "function expectedValueRaceCandidates(circuit){", "function fixedPickLoadStatus(circuit){")
text = remove_between(text, "function fixedValueBox(circuit,picks){", "function smartExpectedValueRaces(){")
text = remove_between(text, "function smartExpectedValueRaces(){", "function selectedRaceBetPreview(r){")

text = text.replace(
    "selectedSectionsOpen={selected:false,value:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false},value:{'中央':false,'地方':false}};",
    "selectedSectionsOpen={selected:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false}};",
)
text = text.replace("      smartExpectedValueRaces()+\n", "")
text = text.replace(
    "if(k==='selected'||k==='value')selectedSectionsOpen[k]=!!el.open",
    "if(k==='selected')selectedSectionsOpen[k]=!!el.open",
)
text = text.replace(
    "if((k==='selected'||k==='value')&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open",
    "if(k==='selected'&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open",
)
text = text.replace("label=kind==='value'?'期待値判定':'厳選判定';", "label='厳選判定';")
text = text.replace("高期待値ゲート通過", "買い目品質ゲート通過")
text = text.replace("期待値品質スコア不足", "買い目品質スコア不足")

for forbidden in (
    "function smartExpectedValueRaces(",
    "function expectedValueRaceCandidates(",
    "function eliteValueRaceCut(",
    "function fixedValueBox(",
    ">期待値高レース<",
    "smartExpectedValueRaces()+",
    "selected:false,value:false",
    "高期待値ゲート通過",
    "期待値品質スコア不足",
):
    if forbidden in text:
        raise SystemExit(f"value-race feature still present: {forbidden}")

# Special forecast must already exist in the source and is owned by
# arvexq_patch_special_races.py. Do not replace or downgrade it here.
if "function specialForecastRaceCandidates(){" not in text or "function smartSpecialForecastRaces(){" not in text:
    raise SystemExit("special forecast source unexpectedly missing")

PATH.write_text(text, encoding="utf-8")
print("value-race category removed without touching special forecast/build/PWA policy")

# Selection and trifecta policy passes remain independent and idempotent.
policy = Path("scripts/arvexq_enforce_selection_policy.py")
if policy.exists():
    runpy.run_path(str(policy), run_name="__main__")

mandatory_tri = Path("scripts/arvexq_force_mandatory_trifecta.py")
if mandatory_tri.exists():
    runpy.run_path(str(mandatory_tri), run_name="__main__")
