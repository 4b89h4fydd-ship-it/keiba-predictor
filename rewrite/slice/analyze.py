"""Evidence-driven, explicitly uncalibrated ranking and four-stage scenarios.

No odds, target race outcomes, current career statistics or legacy marks are inputs.
All coefficients are declared heuristic parameters, not claimed fitted performance.
"""
from collections import defaultdict
from datetime import date
from math import exp, isfinite
from statistics import fmean

HORSE_FIELDS = ('horse_id','number','frame','name','sex','age','jockey','trainer',
                'carried_weight','body_weight','pedigree','odds')
PAST_FIELDS = ('date','track','surface','distance','field_size','finish',
               'time_seconds','margin_seconds','corners','last3f','class','opponent','going')
EXTENDED = ('training', 'verified_start_timing', 'verified_video', 'full_opponent_ratings')
PARAMETERS = {'中央': {'recency_days':180, 'distance_scale':600},
              '地方': {'recency_days':90, 'distance_scale':300}}


def missing(value):
    return value is None or value == '' or value == []


def validate(race):
    if race['circuit'] not in PARAMETERS or race['track'] in {'帯広','帯広ば','帯広ばんえい','Obihiro'}:
        raise ValueError('unsupported circuit/venue')
    if any(word in race['title'] for word in ('新馬', '障害')):
        raise ValueError('debut/jumps models are not implemented in this validation slice')
    horses = race['horses']
    if any(h.get('cancelled') for h in horses):
        raise ValueError('current-card cancellations require a fresh independently verified active roster')
    proof = race.get('roster_check', {})
    if not proof.get('exact_number_name_match') or proof.get('independent_horses') != len(horses):
        raise ValueError('independent full-field roster verification required')
    if len(horses) != race['declared_count'] or len(horses) < 2:
        raise ValueError('incomplete field')
    if len({h['number'] for h in horses}) != len(horses) or len({h['horse_id'] for h in horses}) != len(horses):
        raise ValueError('duplicate field identity')
    for horse in horses:
        if not horse['name'] or not horse['histories']:
            raise ValueError('incomplete horse evidence')
        if not horse['source'].get('sha256') or not horse['source'].get('fetched_at'):
            raise ValueError('acquisition provenance required')
        seen = set()
        for past in horse['histories']:
            if past['date'] >= race['date']:
                raise ValueError('same-race/future leakage')
            if not (past['field_size'] and past['finish'] and 1 <= past['finish'] <= past['field_size']):
                raise ValueError('invalid historical finish')
            if past['race_key'] is not None and past['race_key'] in seen:
                raise ValueError('duplicate past race')
            if past['race_key'] is not None:
                seen.add(past['race_key'])
            if past['corners'] and any(n < 1 or n > past['field_size'] for n in past['corners']):
                raise ValueError('invalid historical corner')
            for field in ('time_seconds','margin_seconds','last3f'):
                if past[field] is not None and not isfinite(past[field]):
                    raise ValueError('nonfinite historical measurement')


def quality(race):
    horses = []
    missing_total = total = 0
    for horse in race['horses']:
        fields = {}
        for field in HORSE_FIELDS + EXTENDED:
            absent = field in EXTENDED or missing(horse.get(field))
            fields[field] = {'status':'missing' if absent else 'observed',
                             'reason':'not_available_in_selected_public_sources' if absent else None,
                             'source':horse['source']['url'], 'fetched_at':horse['source']['fetched_at'],
                             'source_sha256':horse['source']['sha256']}
        past_missing = []
        for past in horse['histories']:
            absent = [f for f in PAST_FIELDS if missing(past.get(f))]
            past_missing.append({'race_key':past['race_key'], 'missing_fields':absent,
                                 'reason':'not_published_or_not_extracted' if absent else None,
                                 'source':past['source']})
        core_missing = sum(fields[f]['status']=='missing' for f in HORSE_FIELDS)
        history_missing = sum(len(x['missing_fields']) for x in past_missing)
        denominator = len(HORSE_FIELDS) + len(PAST_FIELDS)*len(past_missing)
        numerator = core_missing + history_missing
        total += denominator
        missing_total += numerator
        horses.append({'number':horse['number'],'fields':fields,'past_missing':past_missing,
                       'missing':numerator,'expected':denominator,'missing_rate':numerator/denominator})
    return {'horses':horses, 'missing':missing_total, 'expected':total,
            'missing_rate':missing_total/total, 'definition':{'horse_fields':list(HORSE_FIELDS),'past_fields':list(PAST_FIELDS),
            'extended_fields_excluded_from_core_rate':list(EXTENDED)},
            'extended_missing_rate':1.0,
            'field_count_basis':race.get('field_count_basis'),
            'status':'complete_roster_with_declared_missing_fields'}


def analyze(race):
    validate(race)
    params = PARAMETERS[race['circuit']]
    rows = []
    shared = defaultdict(list)
    for horse in race['horses']:
        for past in horse['histories']:
            if past['race_key'] is None:
                continue
            shared[past['race_key']].append({'number':horse['number'], 'finish':past['finish'],
                                           'time_seconds':past['time_seconds']})
    for horse in race['horses']:
        evidence = []
        stage_observations = {'start':[], 'thirdCorner':[], 'fourthCorner':[], 'straight':[]}
        for past in horse['histories']:
            days = (date.fromisoformat(race['date'])-date.fromisoformat(past['date'])).days
            distance_gap = abs(past['distance']-race['distance']) if past['distance'] else None
            relevance = exp(-days/params['recency_days'])
            if distance_gap is not None:
                relevance *= 1/(1+distance_gap/params['distance_scale'])
            relevance *= 1.25 if past['track']==race['track'] else 1
            relevance *= 1 if past['surface']==race['surface'] else .5
            performance = 1-(past['finish']-1)/max(1,past['field_size']-1)
            margin_component = None
            if past['margin_seconds'] is not None and past['distance']:
                # Signed seconds per km against the winner/runner-up, not length conversion.
                margin_component = past['margin_seconds']*1000/past['distance']
                performance -= .1*margin_component
            evidence.append({'race_key':past['race_key'],'date':past['date'],
                             'finish_percentile':1-(past['finish']-1)/max(1,past['field_size']-1),
                             'margin_seconds_per_km':margin_component,'performance_index':performance,
                             'relevance_weight':relevance, 'distance_gap':distance_gap,
                             'same_course':past['track']==race['track'], 'class_observed':past['class'],
                             'shared_opponents':[x for x in shared[past['race_key']] if x['number']!=horse['number']],
                             'named_opponent':past['opponent'], 'source':past['source']})
            corners = past['corners']
            denominator = max(1,past['field_size']-1)
            if corners and len(corners) >= 2:
                stage_observations['start'].append((corners[0]-1)/denominator)
                stage_observations['thirdCorner'].append((corners[-2]-1)/denominator)
                stage_observations['fourthCorner'].append((corners[-1]-1)/denominator)
                stage_observations['straight'].append((past['finish']-1)/denominator)
        if any(not values for values in stage_observations.values()):
            raise ValueError(f'cannot generate four stages without positional evidence: {horse["number"]}')
        ability = sum(e['performance_index']*e['relevance_weight'] for e in evidence)/sum(e['relevance_weight'] for e in evidence)
        rows.append({'number':horse['number'],'name':horse['name'],'ability':ability,
                     'evidence':evidence,'position_basis':{k:fmean(v) for k,v in stage_observations.items()},
                     'position_samples':{k:len(v) for k,v in stage_observations.items()},
                     'aptitude':{'same_course_starts':sum(e['same_course'] for e in evidence),
                                 'near_distance_starts':sum(e['distance_gap'] is not None and e['distance_gap']<=200 for e in evidence)},
                     'days_since_last_start':(date.fromisoformat(race['date'])-date.fromisoformat(max(h['date'] for h in horse['histories']))).days})
    leaders = [r['number'] for r in rows if r['position_basis']['start'] < .33]
    scenarios = []
    for name, pace_effect in (('通常',0.0),('ハイペース',.18),('スローペース',-.12)):
        stages = {}
        for index,key in enumerate(('start','thirdCorner','fourthCorner','straight')):
            projected = []
            for row in rows:
                base = row['position_basis'][key]
                front_exposure = .5-row['position_basis']['start']
                # Front-runners incur more late fatigue under high pace, benefit under slow pace.
                score = base + pace_effect*front_exposure*(index/3)
                projected.append({'number':row['number'],'position_index':score,
                                  'basis_samples':row['position_samples'][key]})
            projected.sort(key=lambda x:(x['position_index'],x['number']))
            stages[key] = [dict(x,position=i+1) for i,x in enumerate(projected)]
        scenarios.append({'name':name, 'stages':stages, 'front_contenders':leaders,
                          'pace_probability':None,
                          'conditions':f'先行候補{len(leaders)}頭（馬番{",".join(map(str,leaders)) or "該当なし"}）。'
                                       + ('先行争いが続き消耗する場合、後方待機馬の順位を上方修正。' if pace_effect>0 else
                                          '前半を抑えられた場合、先行馬の位置優位が残る。' if pace_effect<0 else '過去の位置取り傾向が継続する場合。')})
    for row in rows:
        finishes = [next(x['position'] for x in s['stages']['straight'] if x['number']==row['number']) for s in scenarios]
        row['scenario_positions'] = finishes
        row['ranking_index'] = .75*row['ability']+.25*(1-(fmean(finishes)-1)/max(1,len(rows)-1))
    ranking = sorted(rows,key=lambda r:(-r['ranking_index'],r['number']))
    for i,row in enumerate(ranking):
        row.update(mark='◎○▲△☆'[i] if i<5 else '', win_probability=None,top2_probability=None,top3_probability=None)
    return {'version':'arvexq-independent-slice-v1','race_id':race['id'],
            'analysis_type':'retrospective','status':'ranked-unvalidated','production_eligible':False,
            'model_segment':race['circuit'], 'parameters':params,
            'method':'declared heuristic; rank percentile, signed margin/km, recency and course relevance; no fitted probabilities',
            'quality':quality(race),'rows':ranking,'scenarios':scenarios,
            'stage_limitations':{'start':'最初に観測されたコーナー順位を代理使用。実測スタート性能ではない。',
                                 'thirdCorner':'過去の最後から2番目のコーナー順位を使用。',
                                 'fourthCorner':'過去の最終コーナー順位を使用。',
                                 'straight':'最終コーナーから着順への変化を直線の代理使用。直線の実測位置ではない。'},
            'bets':[], 'bet_decision':'見送り',
            'bet_reasons':['確率が未校正・未検証','オッズは事後取得の最終表示値で、発走前の時点証明がない'],
            'calibration_status':'not-validated','video_status':'not-used-unlicensed-unverified',
            'limitations':['事後取得の再現検証。発走前予想の原本ではない。',
                           '直線・スタートは代理特徴。調教、完全な相手レーティング、血統効果は評価していない。']}
