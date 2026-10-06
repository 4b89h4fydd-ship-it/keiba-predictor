#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")

# Keep the race classification and both existing call sites, but change the
# historical "force" helper into a review-only guard. Graded races and Kochi
# Final must always REVIEW the trifecta, never manufacture one when the normal
# order-confidence gate rejected it.
start = text.find("function forceMandatoryTrifecta(plan,r,p){")
if start < 0:
    raise SystemExit("forceMandatoryTrifecta helper not found")
next_fn = text.find("\nfunction ", start + 1)
if next_fn < 0:
    raise SystemExit("forceMandatoryTrifecta end anchor not found")

replacement = r'''function forceMandatoryTrifecta(plan,r,p){
  if(!plan||!mandatoryTrifectaRace(r))return plan;
  plan.trifectaReviewed=true;
  plan.mandatoryTrifectaReviewed=true;
  if(plan.trifectaDecision==='採用'){
    plan.trifectaReason=plan.trifectaReason||'重賞・高知ファイルの3連単を検討し、順序信頼ゲートを通過。';
    return plan
  }
  plan.trifectaDecision='見送り';
  plan.trifectaReason='重賞・高知ファイルは3連単を必ず検討。今回は順序信頼不足のため見送り。';
  plan.mandatoryTrifecta=false;
  return plan
}
'''
text = text[:start] + replacement + text[next_fn+1:]

# Mandatory races must also show the "reviewed but skipped" copy when order
# confidence is insufficient. Remove the old suppression if it is present.
old_copy = "if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り'&&!mandatoryTrifectaRace(r))lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');"
new_copy = "if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');"
if old_copy in text:
    text = text.replace(old_copy, new_copy, 1)
elif new_copy not in text:
    raise SystemExit("betTransferText trifecta review line not found")

# UI copy must follow the same rule. aiBetRecommendation already renders a
# reviewed/skipped row whenever trifectaDecision is 見送り, so no extra ticket
# injection is allowed here.
for forbidden in (
    "重賞・高知ファイルは3連単チャレンジ必須",
    "mandatory:true",
    "if(plan.decision==='見送り')plan.decision='通常買い'",
):
    if forbidden in text:
        raise SystemExit(f"old forced-trifecta behavior still present: {forbidden}")

for required in (
    "function mandatoryTrifectaRace(r){",
    "function forceMandatoryTrifecta(plan,r,p){",
    "vp=forceMandatoryTrifecta(vp,r,p)",
    "plan=forceMandatoryTrifecta(plan,r,p)",
    "mandatoryTrifectaReviewed=true",
    "今回は順序信頼不足のため見送り",
):
    if required not in text:
        raise SystemExit(f"trifecta review policy missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("graded/Kochi trifecta policy changed from forced ticket to mandatory review with order-confidence gate")
