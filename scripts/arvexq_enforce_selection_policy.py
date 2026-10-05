#!/usr/bin/env python3
from pathlib import Path

PATH = Path('arvexq/ui/static/app.js')
text = PATH.read_text(encoding='utf-8')

# Mandatory prediction races are NOT the same thing as true ARVEXQ selections.
# Keep graded races and Kochi Final as mandatory prediction targets, but never
# promote them to 厳選 unless they independently pass the selection gate.
old_featured = "return !!(r&&(explicitSelectedRace(r)||raceIsGraded(r)||r.isMain||r.mainRace||r.featured||n(r.raceNumber)===11||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))"
new_featured = "return !!(r&&(raceIsGraded(r)||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))"
if old_featured in text:
    text = text.replace(old_featured, new_featured, 1)
elif new_featured not in text:
    raise SystemExit('featured race policy block not found')

# Make the visible 厳選 list genuinely sparse. It may be empty. Do not fill it
# with main/graded/Kochi races merely to have something to show. These stricter
# gates are selection filters, not a claim that any race is literally certain.
old_cut = "var best=n(rows[0].selection&&rows[0].selection.score),central=String((rows[0].race&&rows[0].race.circuit)||'')==='中央',floor=Math.max(central?72:68,best-4),limit=best>=(central?87:84)?3:2;\n  var elite=rows.filter(function(z){var t=z.selection||{},rd=t.readiness||{},central=String((z.race&&z.race.circuit)||'')==='中央';return n(t.score)>=floor&&n(rd.prediction)>=(central?.64:.61)&&n(t.coverage)>=(central?.44:.42)&&n(t.top3mass)>=(central?.58:.60)&&n(t.evidence)>=(central?.38:.36)&&n(t.scenarioProb)>=(central?.24:.22)&&!!t.winnerStable&&n(t.winnerConfidence)>=.60});\n  return elite.slice(0,limit).sort(raceChronologicalCompare)"
new_cut = "var best=n(rows[0].selection&&rows[0].selection.score),central=String((rows[0].race&&rows[0].race.circuit)||'')==='中央',floor=Math.max(central?82:80,best-2),limit=1;\n  var elite=rows.filter(function(z){var t=z.selection||{},rd=t.readiness||{},central=String((z.race&&z.race.circuit)||'')==='中央';return n(t.score)>=floor&&n(rd.prediction)>=(central?.74:.72)&&n(t.coverage)>=(central?.60:.58)&&n(t.top3mass)>=(central?.68:.70)&&n(t.evidence)>=(central?.55:.53)&&n(t.scenarioProb)>=(central?.30:.28)&&!!t.winnerStable&&n(t.winnerConfidence)>=.72});\n  return elite.slice(0,limit).sort(raceChronologicalCompare)"
if old_cut in text:
    text = text.replace(old_cut, new_cut, 1)
elif new_cut not in text:
    raise SystemExit('elite selection cut block not found')

text = text.replace(
    "reason=featured?'本日の厳選/メイン/重賞/高知ファイナル対象。v220は共通着順分布から5券種を生成し、確率差で自動的に点数を絞ります。':",
    "reason=featured?'厳選ゲート通過、または必須予想の重賞/高知ファイナル対象。必須予想は厳選扱いしません。':",
)

# UI copy: selected can be zero. This is deliberate.
text = text.replace(
    '<b>厳選レース</b><small>全レース比較から少数精鋭だけ・時間順</small>',
    '<b>厳選レース</b><small>基準未達なら0件・本当に強い時だけ</small>',
)

PATH.write_text(text, encoding='utf-8')
print('selection policy enforced: true selections separate from graded/Kochi mandatory races')
