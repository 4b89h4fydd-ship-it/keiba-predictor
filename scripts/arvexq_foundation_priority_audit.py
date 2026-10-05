#!/usr/bin/env python3
from __future__ import annotations

import copy
from collections import Counter

import scripts.arvexq_today_old_new_compare as audit
from arvexq.prediction.factor_model import rank_factor_model


def _stage_vote(a, b, pillars):
    aw = bw = compared = 0
    for p in pillars:
        av, bv = a.get(p), b.get(p)
        if av is None or bv is None:
            continue
        compared += 1
        if av > bv:
            aw += 1
        elif bv > av:
            bw += 1
    if aw > bw:
        return 1, compared
    if bw > aw:
        return -1, compared
    return 0, compared


def foundation_rank(detail):
    rows = rank_factor_model(detail.get('horses') or [], detail)
    rows = [dict(r) for r in rows]
    if not rows:
        return []
    for r in rows:
        r['fWins'] = r['fLosses'] = r['fTies'] = 0
        r['foundationRankSum'] = r['pillarRanks']['ability'] + r['pillarRanks']['record']
        r['secondaryRankSum'] = r['pillarRanks']['suitability'] + r['pillarRanks']['pace']
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            v, compared = _stage_vote(a, b, ('ability', 'record'))
            if v == 0:
                v2, compared2 = _stage_vote(a, b, ('suitability', 'pace'))
                if compared == 0 or v == 0:
                    v = v2
                if v == 0:
                    sa, sb = a.get('support'), b.get('support')
                    if (compared + compared2) > 0 and sa is not None and sb is not None and sa != sb:
                        v = 1 if sa > sb else -1
            if v > 0:
                a['fWins'] += 1; b['fLosses'] += 1
            elif v < 0:
                b['fWins'] += 1; a['fLosses'] += 1
            else:
                a['fTies'] += 1; b['fTies'] += 1
    rows.sort(key=lambda r: (
        -r['fWins'], r['fLosses'],
        r['foundationRankSum'], r['secondaryRankSum'], r['pillarRanks']['support'],
        -r.get('primaryPillarCoverage', 0), -r.get('sample', 0),
        int(r['horse'].get('horseNumber') or 999),
    ))
    return rows


def pos(order, horse_no):
    return order.index(horse_no) + 1 if horse_no in order else 999


def pct(x, n):
    return f"{x}/{n} ({100*x/n:.1f}%)" if n else '—'


def main():
    url = audit.API_BASE + '/api/day?' + audit.urllib.parse.urlencode({'date': audit.TARGET_DATE, 'details': '1'})
    payload = audit.api_json(url)
    out = []
    changed = Counter()
    for detail in payload.get('details') or []:
        if not isinstance(detail, dict):
            continue
        order = audit.finish_order(detail)
        if not order:
            continue
        snap, _ = audit.find_prerace_snapshot(detail)
        old, _ = audit.legacy_marks(detail, snap)
        base = audit.scrub_postrace(copy.deepcopy(detail))
        current_rows = rank_factor_model(base.get('horses') or [], base)
        foundation_rows = foundation_rank(base)
        if not old or not current_rows or not foundation_rows:
            continue
        old_best = next((n for n, m in old.items() if m == '◎'), 0)
        current_best = int(current_rows[0]['horse'].get('horseNumber') or 0)
        foundation_best = int(foundation_rows[0]['horse'].get('horseNumber') or 0)
        if current_best != foundation_best:
            changed['changed'] += 1
            cp, fp = pos(order, current_best), pos(order, foundation_best)
            if fp < cp: changed['improved'] += 1
            elif fp > cp: changed['worsened'] += 1
            else: changed['equal'] += 1
        winner = order[0]
        foundation_numbers = [int(r['horse'].get('horseNumber') or 0) for r in foundation_rows]
        row = {
            'track': str(detail.get('track') or detail.get('venue') or ''),
            'race': audit.iv(detail.get('raceNumber', detail.get('raceNo'))),
            'winner': winner,
            'old': old_best, 'oldPos': pos(order, old_best),
            'current': current_best, 'currentPos': pos(order, current_best),
            'foundation': foundation_best, 'foundationPos': pos(order, foundation_best),
            'winnerFoundationRank': foundation_numbers.index(winner)+1 if winner in foundation_numbers else 999,
            'topFoundation': [
                {
                    'n': int(r['horse'].get('horseNumber') or 0),
                    'ability': r.get('ability'), 'record': r.get('record'),
                    'suitability': r.get('suitability'), 'pace': r.get('pace'),
                    'support': r.get('support'),
                    'counts': r.get('evidenceCounts'), 'sample': r.get('sample'),
                }
                for r in foundation_rows[:3]
            ],
        }
        out.append(row)
    n = len(out)
    def count(key, limit): return sum(r[key] <= limit for r in out)
    print(f'FOUNDATION PRIORITY AUDIT {audit.TARGET_DATE} n={n}')
    print('metric\tOLD\tCURRENT_V3\tFOUNDATION')
    for label, lim in [('◎1着',1),('◎連対',2),('◎3着内',3)]:
        print(f"{label}\t{pct(count('oldPos',lim),n)}\t{pct(count('currentPos',lim),n)}\t{pct(count('foundationPos',lim),n)}")
    print(f"勝ち馬TOP3\t-\t-\t{pct(count('winnerFoundationRank',3),n)}")
    print(f"勝ち馬TOP7\t-\t-\t{pct(count('winnerFoundationRank',7),n)}")
    print('CHANGES', dict(changed))
    print('MISSES/CHANGED')
    for r in out:
        if r['current'] != r['foundation'] or r['foundationPos'] >= 4:
            print(f"{r['track']} {r['race']}R win={r['winner']} old={r['old']}({r['oldPos']}) current={r['current']}({r['currentPos']}) foundation={r['foundation']}({r['foundationPos']}) winnerRank={r['winnerFoundationRank']} top={r['topFoundation']}")

if __name__ == '__main__':
    main()
