"""Replacement forecast challenger: learned evidence -> scenarios -> roles -> bets.

Not installed in production until real-data and cross-runtime acceptance passes.
An absent trained model never falls back to the retired fixed-weight candidate.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from statistics import median

from arvexq.betting.scenario_tickets import compare_tickets
from arvexq.prediction.learned_scenarios import VERSION, active_horses, predict_model, race_evidence
from arvexq.prediction.prerace_archive import JST, post_at

GRADE_DEFINITIONS = {
    'A': '未使用データで検証済みの方式で勝ち切りと安定性の根拠が揃う',
    'B': '観測範囲の根拠が揃い展開比較でも有力だが実測精度は未検証',
    'C': '履歴の欠損または展開・推定の不確実性が大きい',
}
MARK_DEFINITIONS = {
    '◎': '勝ち切りが最有力で上位入線の安定性も比較上位の中心馬',
    '○': '中心馬に対する勝ち切りの逆転候補', '▲': '展開変化にも上位入線の可能性を残す有力馬',
    '△': '条件次第で上位を狙う相手', '☆': '特定の展開で中心馬を逆転する候補',
    '注': '追い上げなど見落としやすい観測根拠を持つ馬',
}


def _name(value):
    # Race numbers, ASCII names and embedded numeric horse-name suffixes cannot
    # leak into the Japanese-only prose. Identity remains in structured rows.
    text = re.sub(r'[^ぁ-ゖァ-ヺ一-龯々ー]', '', str(value or ''))
    return text or 'この馬'


def _decide(analysis):
    reports, scenarios = analysis['reports'], analysis['scenarios']
    if not scenarios:
        return {}, {}, {}
    ranges = {}
    for report in reports:
        no = report['horseNumber']
        wins = [s['probabilities'][no]['win'] for s in scenarios]
        top2 = [s['probabilities'][no]['top2'] for s in scenarios]
        podium = [s['probabilities'][no]['top3'] for s in scenarios]
        ranges[no] = {'win': [min(wins), max(wins)], 'top3': [min(podium), max(podium)], 'top2': [min(top2), max(top2)]}
    win_leader = min(ranges, key=lambda n: (-ranges[n]['win'][0], -ranges[n]['top3'][0], n))
    stability = median(p['top3'][0] for p in ranges.values())
    # Do not quietly choose a different, lower-win horse as a second axis.
    if ranges[win_leader]['top3'][0] < stability:
        return {}, ranges, {'reason': '勝ち切り最有力馬の安定性が比較上位に届かない'}
    marks, reasons = {win_leader: '◎'}, {win_leader: '各展開の勝ち切り下限が最上位で上位入線の安定性も比較上位'}
    remaining = set(ranges)-{win_leader}
    if remaining:
        rival = min(remaining, key=lambda n: (-ranges[n]['win'][1], -ranges[n]['win'][0], n))
        marks[rival] = '○'; reasons[rival] = '成立可能な展開で勝ち切りの逆転可能性が最も高い相手'
        remaining.remove(rival)
    if remaining:
        third = min(remaining, key=lambda n: (-ranges[n]['top3'][0], n))
        marks[third] = '▲'; reasons[third] = '展開変化を含めた上位入線の下限が残る相手の中で最上位'
        remaining.remove(third)
    for no in sorted(remaining):
        report = next(r for r in reports if r['horseNumber'] == no)
        if any(s['probabilities'][no]['win'] > s['probabilities'][win_leader]['win'] for s in scenarios):
            marks[no] = '☆'; reasons[no] = '位置取りが変わる想定の中に中心馬を勝ち切りで上回る場合がある'
        elif (report['featureValues']['closing_gain'] or 0) > 0:
            marks[no] = '注'; reasons[no] = '過去走で直線の追い上げが観測されている'
        elif ranges[no]['top3'][1] >= stability:
            marks[no] = '△'; reasons[no] = '有利な想定では上位入線の可能性が比較水準に達する'
    return marks, ranges, reasons


def build_forecast(detail, model=None):
    result = deepcopy(detail)
    start = post_at(detail)
    retrospective = bool(detail.get('result')) or bool(start and datetime.now(JST) >= start)
    result['analysisType'] = 'retrospective' if retrospective else 'preoff-candidate'
    result['analysisLabel'] = '事後分析' if retrospective else '発走前の検証候補'
    result['predictionModelVersion'] = result['markEngineVersion'] = VERSION
    result['markDefinitions'], result['gradeDefinitions'] = MARK_DEFINITIONS.copy(), GRADE_DEFINITIONS.copy()
    result['probabilityModelStatus'] = 'uncalibrated'
    result['productionEligible'] = False
    if model is None:
        analysis = {'reports': race_evidence(detail), 'scenarios': [], 'status': 'missing-trained-model'}
    else:
        analysis = predict_model(detail, model)
    result['scenarioAnalysis'] = analysis
    reports = {r['horseNumber']: r for r in analysis['reports']}
    marks, ranges, reasons = _decide(analysis)
    active = {int(h['horseNumber']) for h in active_horses(detail)}
    head = next((no for no, mark in marks.items() if mark == '◎'), 0)
    result['predictionStatus'] = 'candidate-analysis' if head else (
        'no-unified-honmei' if analysis['scenarios'] else analysis['status'])
    result['honmeiDecision'] = {'version': VERSION, 'horseNumber': head, 'axisHorseNumber': head,
                                'role': 'win-axis', 'eligible': False, 'displayHonmei': bool(head),
                                'confidenceGrade': 'B' if head and all(r['careerComplete'] for r in reports.values()) else 'C',
                                'fixedAxisAllowed': False,
                                'reason': reasons.get(head) or reasons.get('reason') or '検証済み学習モデルまたは全頭根拠が不足'}
    prose = []
    if len(analysis['scenarios']) > 1:
        prose.append('通常の隊列に加え、前の位置を取り合う場合と後ろに控える場合の影響を比較する。展開の発生頻度は未確認であり、特定の流れを断定しない。')
    elif analysis['scenarios']:
        prose.append('通常の隊列だけを比較する。位置取りの観測不足により、前進や後方待機の展開比較はできない。')
    else:
        prose.append('学習済みの検証モデルまたは全頭の過去走が不足しており、本命と買い目の確定を見送る。')
    if head:
        prose.append(_name(reports[head]['name'])+'を中心候補とする。'+reasons[head]+'ためである。ただし推定精度の実測検証が済むまでは軸としての信頼を断定しない。')
    for horse in result.get('horses', []):
        if not isinstance(horse, dict):
            continue
        no = int(horse.get('horseNumber') or 0)
        ev = horse.setdefault('integratedEvaluation', {})
        ev.update({'mark': marks.get(no, ''), 'markSource': VERSION, 'markEngineVersion': VERSION,
                   'honmeiRole': 'win-axis' if no == head else '', 'podiumAxisEligible': no == head and bool(head),
                   'modelProbabilities': ranges.get(no, {}),
                   'modelProbabilityPercentRanges': {k: [100*v for v in bounds] for k, bounds in ranges.get(no, {}).items()}, 'markReason': reasons.get(no, ''),
                   'wholeCareerEvidence': reports.get(no, {}), 'grade': 'C'})
        if no not in active:
            continue
        r = reports[no]
        parts = [_name(r['name'])+'は']
        if not r['observedStarts']:
            parts.append('日付を確認できる過去走がなく、能力と展開適性を判断できない。')
        else:
            f = r['featureValues']
            if f['closing_gain'] is not None and f['closing_gain'] > 0:
                parts.append('直線で位置を上げた実績がある。')
            elif f['closing_gain'] is not None and f['closing_gain'] < 0:
                parts.append('直線で位置を下げる傾向があり、仕掛けと持続力が課題となる。')
            else:
                parts.append('確認できた着順と位置取りから比較する。')
            if r['transfer']:
                parts.append(r['transfer']+'で、相手関係が変わる影響の大きさは未検証である。')
            if f['same_distance_finish'] is None or f['same_surface_finish'] is None:
                parts.append('今回と同じ距離や馬場種別の比較材料に不足がある。')
            if not r['careerComplete']:
                parts.append('過去走の網羅性は未確認であり、確認範囲の成績を通算実績とは断定しない。')
        if no in reasons:
            parts.append(reasons[no]+'。')
        ev['forecastText'] = ''.join(parts)
        prose.append(ev['forecastText'])
    result['forecastText'] = ''.join(prose)
    result['recommendedBetPlan'] = (compare_tickets(result, analysis['scenarios'], model_version=VERSION)
                                    if head else {'decision': '見送り', 'items': [], 'reason': result['honmeiDecision']['reason']})
    # preRacePrediction / preRaceBet remain byte-for-byte equivalent values.
    # Never seal this retrospective analysis as an original forecast.
    return result
