from __future__ import annotations

# Transitional extraction of evaluation_core from app.py.
# The block is executed in the caller namespace to preserve legacy global lookup.
# Historical rankers (v207/v212/v213/v215/v218/v313/v317) were deleted.
# This module retains only observed auxiliary race context and volatility;
# all live marks use arvexq.prediction.observed_model.
SOURCE = (
    'def _integrated_evaluation(horse: dict, race: dict) -> dict:\n'
    '    """Evidence-only score; 50 is an explicit neutral prior, never an observed fact."""\n'
    "    all_runs = [r for r in (horse.get('allPastRuns') or horse.get('recentRaces') or [])\n"
    "                if isinstance(r, dict) and (not r.get('date') or str(r['date']) < str(race.get('date') or '9999'))]\n"
    "    jump = race.get('analysisMode') == '障害' or _is_jump_run(race)\n"
    "    debut = not all_runs and (horse.get('debutNoHistory') or race.get('analysisMode') == '新馬' or '新馬' in str(race.get('title')))\n"
    '    runs = [r for r in all_runs if _is_jump_run(r)] if jump else [r for r in all_runs if not _is_jump_run(r)]\n'
    '    gap = 0\n'
    '    if all_runs:\n'
    '        try:\n'
    "            gap = (dt_date.fromisoformat(race['date']) - max(dt_date.fromisoformat(r['date']) for r in all_runs if r.get('date'))).days\n"
    '        except (ValueError, KeyError):\n'
    '            pass\n'
    "    transfer = bool(horse.get('isTransfer') or horse.get('transferFrom') or\n"
    "                    (all_runs and all_runs[0].get('circuit') and all_runs[0]['circuit'] != race.get('circuit')))\n"
    "    mode = '障害' if jump else '新馬' if debut else '転入馬' if transfer else '長期休養馬' if gap >= 180 else '通常馬'\n"
    '    components, weights, counts = {}, {}, {}\n'
    '    def add(key, value, weight, count=1):\n'
    '        value = _evaluation_number(value)\n'
    '        if value is not None and 0 <= value <= 1:\n'
    '            components[key], weights[key], counts[key] = value, weight, count\n'
    '    def quality(run):\n'
    "        fin, size = _evaluation_number(run.get('finish')), _evaluation_number(run.get('fieldSize'))\n"
    '        if fin is None or size is None or not 1 <= fin <= size or size < 2:\n'
    '            return None\n'
    '        return 1 - (fin - 1) / (size - 1)\n'
    '    observed = [(r, quality(r)) for r in runs if quality(r) is not None]\n'
    '    if observed:\n'
    '        # Every observed start contributes. Recency weighting never drops old starts.\n'
    '        ws = [1 / (1 + i * .15) for i in range(len(observed))]\n'
    "        add('racePerformance', sum(q*w for (_, q), w in zip(observed, ws))/sum(ws), .32, len(observed))\n"
    '        representative, best = max(observed, key=lambda x: x[1])\n'
    "        horse['representativeRun'] = dict(representative)\n"
    "        add('representative', best, .10, len(observed))\n"
    "        for key, field in [('courseFit','track'), ('distanceFit','distance'), ('goingFit','condition')]:\n"
    '            target = race.get(field)\n'
    "            matched = [q for r,q in observed if target not in (None,'','不明') and r.get(field) == target]\n"
    '            if matched: add(key, sum(matched)/len(matched), .12, len(matched))\n'
    '    # Named pedigree/jockey information counts as coverage, but names are never converted to invented ability.\n'
    "    score_fields = [('pedigreeScore',.16),('distanceSuitabilityScore',.12),('surfaceSuitabilityScore',.12),\n"
    "                    ('drawScore',.06),('bodyWeightScore',.05),('opponentLevelScore',.12),('lapScore',.08),('conditionChangeScore',.08)]\n"
    '    if jump:\n'
    "        score_fields += [('jumpJockeyScore',.18),('jumpTrainerScore',.14)]\n"
    '        completed = []\n'
    '        for run in runs:\n'
    "            finish = _evaluation_number(run.get('finish'))\n"
    "            status = str(run.get('status') or run.get('finishStatus') or run.get('finish') or '')\n"
    '            if finish is not None and finish > 0: completed.append(1)\n'
    "            elif re.search('中止|落馬|失格|競走中止|DNF|DQ',status,re.I): completed.append(0)\n"
    "        if completed: add('jumpCompletion',sum(completed)/len(completed),.30,len(completed))\n"
    '        flat = [quality(r) for r in all_runs if not _is_jump_run(r) and quality(r) is not None]\n'
    "        if flat: add('flatSupportingAbility',sum(flat)/len(flat),.05,len(flat))\n"
    "        roles = [('jumpJockeyStats','jumpJockeyResults',.18),('jumpTrainerStats','jumpTrainerResults',.14)]\n"
    '    else:\n'
    "        score_fields += [('jockeyScore',.12),('trainerScore',.12)]\n"
    "        roles = [('jockeyStats','jockeyResults',.12),('trainerStats','trainerResults',.12)]\n"
    '    for field,weight in score_fields: add(field,horse.get(field),weight)\n'
    '    for field,key,weight in roles:\n'
    '        stats = horse.get(field) or {}\n'
    '        if isinstance(stats,dict):\n'
    "            starts = _evaluation_number(stats.get('starts') or stats.get('runs'))\n"
    "            wins = _evaluation_number(stats.get('wins'))\n"
    '            if starts and starts > 0 and wins is not None and 0 <= wins <= starts:\n'
    '                add(key,wins/starts,weight,int(starts))\n'
    "    base = ['name','sex','age','carriedWeight','jockey','trainer','frameNumber','bodyWeight','pedigree']\n"
    "    coverage = {k: horse.get(k) not in (None,'',{},[]) for k in base}\n"
    '    if not debut:\n'
    "        coverage.update({'pastRuns':bool(runs),'finish':bool(observed),\n"
    "                         'corners':any(r.get('cornerPositions') for r in runs),\n"
    "                         'opponentLevel':horse.get('opponentLevelScore') is not None,\n"
    "                         'prize':horse.get('prizeMoneyAtRace') is not None})\n"
    "    if jump: coverage.update({'jumpHistory':bool(runs),'jumpJockey':bool(horse.get('jumpJockeyStats') or horse.get('jumpJockeyScore') is not None),\n"
    "                              'jumpTrainer':bool(horse.get('jumpTrainerStats') or horse.get('jumpTrainerScore') is not None)})\n"
    '    fullness = round(100*sum(coverage.values())/len(coverage))\n'
    '    rich = len(components) >= 6 and fullness >= 80 and (debut or len(observed)>=5)\n'
    "    tier = 'フルデータ評価' if rich else '限定データ評価' if len(components)>=2 else '基礎データ評価'\n"
    "    confidence = '高' if rich and not transfer and gap<180 else '中' if len(components)>=3 and fullness>=50 and gap<365 else '低'\n"
    '    score = 100*sum(components[k]*weights[k] for k in components)/sum(weights.values()) if components else 50.0\n'
    "    reasons = [mode+'モデル',tier]\n"
    "    if not components: reasons.append('比較根拠なし：中立点50、同点は馬番順（能力差を示さない）')\n"
    "    if debut: reasons.append('過去走0は正常。取得済みの基礎情報で評価')\n"
    "    if jump: reasons.append('障害成績・完走・専用騎手厩舎を優先。平地実績は補助のみ')\n"
    "    if gap>=180: reasons.append(str(gap)+'日ぶり：信頼度を調整')\n"
    "    if transfer: reasons.append('転入：条件間の比較に不確実性あり')\n"
    "    return {'version':AI_EVALUATION_VERSION,'score':round(score,1),'mode':mode,'tier':tier,\n"
    "            'dataCompleteness':fullness,'confidence':confidence,'samples':len(runs),'allRunCount':len(all_runs),\n"
    "            'components':components,'weights':weights,'sampleCounts':counts,'coverage':coverage,\n"
    "            'missing':[k for k,v in coverage.items() if not v], 'neutralPrior':not bool(components),\n"
    "            'reasons':reasons,'reason':' / '.join(reasons),'historyNotApplicable':bool(debut),\n"
    "            'scoreMeaning':'比較用のモデル評価点。実測値・的中確率ではない'}\n"
    '\n'
    '\n'
    'def _v207_norm01(value, default=.5):\n'
    '    try:\n'
    '        x=float(value)\n'
    '        if not math.isfinite(x): return default\n'
    '    except (TypeError,ValueError):\n'
    '        return default\n'
    '    if x > 1.5: x /= 100.0\n'
    '    return max(0.0,min(1.0,x))\n'
    '\n'
    '\n'
    'def _v207_component(e: dict, *names: str, default=.5):\n'
    '    c=e.get("components") or {}\n'
    '    for name in names:\n'
    '        if c.get(name) is not None:\n'
    '            return _v207_norm01(c.get(name),default)\n'
    '    return default\n'
    '\n'
    '\n'
    'def _v207_winner_score(horse: dict, legacy_p1: float) -> float:\n'
    '    """v206 holdout-promoted winner ranker, used only on validated circuits.\n'
    '\n'
    '    The feature whitelist exactly mirrors backtest_v206.py. Result, payout,\n'
    '    win odds and popularity are deliberately absent.\n'
    '    """\n'
    '    e=horse.get("integratedEvaluation") or {}\n'
    '    pm=horse.get("precomputedMetrics") or {}\n'
    '    fit=pm.get("fit") or {}\n'
    '    st=pm.get("style") or {}\n'
    '    try:samples=max(int(st.get("samples") or 0),int(e.get("samples") or 0))\n'
    '    except (TypeError,ValueError):samples=0\n'
    '    fullness=max(0.0,min(1.0,float(e.get("dataCompleteness") or 50)/100.0))\n'
    '    evidence=max(0.0,min(1.0,.55*min(1.0,samples/5.0)+.45*fullness))\n'
    '    late_role=max(0.0,min(1.0,\n'
    '        .42*_v207_norm01(st.get("moved3"),0)+\n'
    '        .32*_v207_norm01(st.get("mid"),0)+\n'
    '        .26*_v207_norm01(st.get("close"),0)))\n'
    '    f={\n'
    '        "p1_saved":_v207_norm01(legacy_p1,.5),\n'
    '        "eval_score":_v207_norm01(e.get("score"),.5),\n'
    '        "race_perf":_v207_component(e,"racePerformance",default=.5),\n'
    '        "representative":_v207_component(e,"representative",default=.5),\n'
    '        "distance":_v207_component(e,"distanceFit",default=_v207_norm01(fit.get("distance"),.5)),\n'
    '        "track":_v207_component(e,"courseFit",default=_v207_norm01(fit.get("track"),.5)),\n'
    '        "going":_v207_component(e,"goingFit",default=_v207_norm01(fit.get("condition"),.5)),\n'
    '        "level":_v207_component(e,"opponentLevelScore",default=_v207_norm01(fit.get("level"),.5)),\n'
    '        "lap":_v207_component(e,"lapScore",default=.5),\n'
    '        "jockey":_v207_component(e,"jockeyScore","jockeyResults",default=.5),\n'
    '        "trainer":_v207_component(e,"trainerScore","trainerResults",default=.5),\n'
    '        "body":_v207_component(e,"bodyWeightScore",default=.5),\n'
    '        "condition_change":_v207_component(e,"conditionChangeScore",default=.5),\n'
    '        "early3":_v207_norm01(st.get("early3"),0),\n'
    '        "ten":_v207_norm01(st.get("ten"),.5),\n'
    '        "late_role":late_role,\n'
    '        "evidence":evidence,\n'
    '    }\n'
    '    return round(max(0.0,min(1.0,sum(V207_WINNER_WEIGHTS[k]*f[k] for k in V207_WINNER_WEIGHTS)))*100,4)\n'
    '\n'
    '\n'
    'def _v212_role_feature_map(horse: dict) -> dict[str,float]:\n'
    '    e=horse.get("integratedEvaluation") or {}\n'
    '    c=e.get("components") or {}\n'
    '    pm=horse.get("precomputedMetrics") or {}\n'
    '    fit=pm.get("fit") or {}\n'
    '    st=pm.get("style") or {}\n'
    '    try:samples=max(0,int(st.get("samples") or 0))\n'
    '    except (TypeError,ValueError):samples=0\n'
    '    def comp(*names,default=.5):\n'
    '        for name in names:\n'
    '            if c.get(name) is not None:return _v207_norm01(c.get(name),default)\n'
    '        return default\n'
    '    return {\n'
    '        "base":_v207_norm01(e.get("score"),.5),\n'
    '        "perf":comp("racePerformance"),\n'
    '        "rep":comp("representative"),\n'
    '        "dist":_v207_norm01(fit.get("distance"),.5),\n'
    '        "track":_v207_norm01(fit.get("track"),.5),\n'
    '        "going":_v207_norm01(fit.get("condition"),.5),\n'
    '        "level":_v207_norm01(fit.get("level"),.5),\n'
    '        "jockey":comp("jockeyScore","jockeyResults"),\n'
    '        "trainer":comp("trainerScore","trainerResults"),\n'
    '        "body":comp("bodyWeightScore"),\n'
    '        "lap":comp("lapScore"),\n'
    '        "ten":_v207_norm01(st.get("ten"),.5),\n'
    '        "early3":_v207_norm01(st.get("early3"),.0),\n'
    '        "moved3":_v207_norm01(st.get("moved3"),.0),\n'
    '        "front":_v207_norm01(st.get("front"),.0),\n'
    '        "stalk":_v207_norm01(st.get("stalk"),.0),\n'
    '        "mid":_v207_norm01(st.get("mid"),.0),\n'
    '        "close":_v207_norm01(st.get("close"),.0),\n'
    '        "evidence":max(0.0,min(1.0,samples/5.0)),\n'
    '        "data":_v207_norm01(e.get("dataCompleteness"),.5),\n'
    '    }\n'
    '\n'
    '\n'
    'def _v212_p2_score(horse: dict) -> float:\n'
    '    """Validated local-racing second-place role ranker.\n'
    '\n'
    '    Trained chronologically on the same market-blind evidence fields used by ARVEXQ.\n'
    '    It is deliberately not used for JRA until the JRA holdout is available.\n'
    '    """\n'
    '    f=_v212_role_feature_map(horse)\n'
    '    z=V212_P2_MODEL_INTERCEPT+sum(V212_P2_MODEL_COEFFICIENTS[k]*f[k] for k in V212_P2_MODEL_COEFFICIENTS)\n'
    '    z=max(-40.0,min(40.0,z))\n'
    '    prob=1.0/(1.0+math.exp(-z))\n'
    '    return round(prob*100.0,4)\n'
    '\n'
    '\n'
    'def _saved_role_scores(horse: dict) -> tuple[float,float,float]:\n'
    '    """Stable pre-race P1/P2/P3 scores stored with the snapshot.\n'
    '\n'
    '    These are intentionally market-blind. P1 emphasizes repeatable winning evidence;\n'
    '    P2 emphasizes stability/front-hold; P3 allows peak/late-role evidence to surface.\n'
    '    """\n'
    "    e=horse.get('integratedEvaluation') or {}\n"
    "    c=e.get('components') or {}\n"
    "    pm=horse.get('precomputedMetrics') or {}\n"
    "    fit=pm.get('fit') or {}\n"
    "    st=pm.get('style') or {}\n"
    '    def u(v,default=.5):\n'
    '        try:\n'
    '            x=float(v)\n'
    '            return max(0.0,min(1.0,x)) if math.isfinite(x) else default\n'
    '        except (TypeError,ValueError):\n'
    '            return default\n'
    "    base=u(float(e.get('score') or 50)/100)\n"
    "    perf=u(c.get('racePerformance'))\n"
    "    rep=u(c.get('representative'))\n"
    "    track=u(fit.get('track'))\n"
    "    dist=u(fit.get('distance'))\n"
    "    going=u(fit.get('condition'))\n"
    "    level=u(fit.get('level'))\n"
    "    jockey=u(c.get('jockeyScore',c.get('jockeyResults')))\n"
    "    body=u(c.get('bodyWeightScore'))\n"
    "    lap=u(c.get('lapScore'))\n"
    "    ten=u(st.get('ten'))\n"
    "    early3=u(st.get('early3'))\n"
    "    moved3=u(st.get('moved3'))\n"
    "    front=u(st.get('front'))\n"
    "    stalk=u(st.get('stalk'))\n"
    "    mid=u(st.get('mid'))\n"
    "    close=u(st.get('close'))\n"
    "    samples=max(0,int(st.get('samples') or 0))\n"
    '    evidence=min(1.0,samples/5.0)\n'
    '    p1=(base*.26+perf*.20+rep*.15+dist*.10+track*.09+level*.07+going*.04+\n'
    '        jockey*.025+body*.015+lap*.02+ten*.02+evidence*.01)\n'
    '    p2=(base*.18+perf*.19+dist*.08+track*.08+going*.05+early3*.12+stalk*.08+\n'
    '        front*.05+ten*.06+jockey*.025+evidence*.055)\n'
    '    p3=(base*.14+perf*.14+rep*.14+dist*.06+track*.05+level*.05+going*.04+\n'
    '        moved3*.10+mid*.07+close*.08+lap*.06+evidence*.07)\n'
    '    return tuple(round(max(0.0,min(1.0,z))*100,2) for z in (p1,p2,p3))\n'
    '\n'
    '\n'
    '\n'
    'def _v213_rank_percentiles(values):\n'
    '    n=len(values)\n'
    '    if n<=1:return [0.5]*n\n'
    '    out=[]\n'
    '    for v in values:\n'
    '        less=sum(1 for x in values if x < v)\n'
    '        equal=sum(1 for x in values if x == v)\n'
    '        rank=1.0+less+(equal-1)*0.5\n'
    '        out.append((rank-1.0)/(n-1.0))\n'
    '    return out\n'
    '\n'
    '\n'
    'def _v213_zscore(values):\n'
    '    if not values:return []\n'
    '    mean=sum(values)/len(values)\n'
    '    var=sum((x-mean)**2 for x in values)/len(values)\n'
    '    sd=math.sqrt(var)\n'
    '    if sd<1e-9:return [0.0 for _ in values]\n'
    '    return [(x-mean)/sd for x in values]\n'
    '\n'
    '\n'
    'def _v213_softmax(values):\n'
    '    if not values:return []\n'
    '    mx=max(values);ex=[math.exp(max(-60.0,min(60.0,x-mx))) for x in values];s=sum(ex) or 1.0\n'
    '    return [x/s for x in ex]\n'
    '\n'
    '\n'
    'def _v213_feature_rows(detail: dict, horses: list[dict]) -> list[dict[str,float]]:\n'
    '    rows=[];field=max(1,len(horses))\n'
    '    weights=[];ages=[]\n'
    '    for h in horses:\n'
    "        try:w=float(h.get('carriedWeight'));weights.append(w if math.isfinite(w) else None)\n"
    '        except (TypeError,ValueError):weights.append(None)\n'
    "        try:a=float(h.get('age'));ages.append(a if math.isfinite(a) else None)\n"
    '        except (TypeError,ValueError):ages.append(None)\n'
    '    wv=[x for x in weights if x is not None];av=[x for x in ages if x is not None]\n'
    '    wmin,wmax=(min(wv),max(wv)) if wv else (0.0,1.0);amin,amax=(min(av),max(av)) if av else (0.0,1.0)\n'
    '    for idx,h in enumerate(horses):\n'
    "        e=h.get('integratedEvaluation') or {};c=e.get('components') or {};pm=h.get('precomputedMetrics') or {};fit=pm.get('fit') or {};st=pm.get('style') or {}\n"
    '        def cp(*names,default=.5):\n'
    '            for name in names:\n'
    '                if c.get(name) is not None:return _v207_norm01(c.get(name),default)\n'
    '            return default\n'
    "        try:samples=max(int(st.get('samples') or 0),int(e.get('samples') or 0))\n"
    '        except (TypeError,ValueError):samples=0\n'
    "        full=max(0.0,min(1.0,float(e.get('dataCompleteness') or 50)/100.0))\n"
    '        evidence=max(0.0,min(1.0,.55*min(1.0,samples/5.0)+.45*full))\n'
    "        runs=list(h.get('recentRaces') or [])[:5];finish_scores=[];gains=[];earlys=[];front_hold=[];wins=top3=used=0\n"
    '        for rr in runs:\n'
    "            try:fin=int(float(rr.get('finish') or rr.get('finishPosition') or 0))\n"
    '            except (TypeError,ValueError):fin=0\n'
    "            try:fs=max(2,int(float(rr.get('fieldSize') or 12)))\n"
    '            except (TypeError,ValueError):fs=12\n'
    '            if fin>0:\n'
    '                score=max(0.0,min(1.0,1.0-(fin-1)/max(1,fs-1)));finish_scores.append(score);used+=1;wins+=int(fin==1);top3+=int(fin<=3)\n'
    "            corners=rr.get('cornerPositions') or []\n"
    '            if corners and fin>0:\n'
    '                try:first=int(float(corners[0] or 0));last=int(float(corners[-1] or 0))\n'
    '                except (TypeError,ValueError):first=last=0\n'
    '                if last>0:gains.append(max(-1.0,min(1.0,(last-fin)/max(1,fs-1))))\n'
    '                if first>0:earlys.append(max(0.0,min(1.0,1.0-(first-1)/max(1,fs-1))))\n'
    '                if first>0:front_hold.append(1.0 if first<=3 and fin<=3 else 0.0)\n'
    '        avg=sum(finish_scores)/len(finish_scores) if finish_scores else .5;peak=max(finish_scores) if finish_scores else .5;last=finish_scores[0] if finish_scores else .5\n'
    "        no=int(h.get('horseNumber') or 0);w=weights[idx];age=ages[idx]\n"
    '        f={\n'
    "            'eval_score':_v207_norm01(e.get('score'),.5),'race_perf':cp('racePerformance'),'representative':cp('representative'),\n"
    "            'distance':cp('distanceFit',default=_v207_norm01(fit.get('distance'),.5)),'track':cp('courseFit',default=_v207_norm01(fit.get('track'),.5)),\n"
    "            'going':cp('goingFit',default=_v207_norm01(fit.get('condition'),.5)),'level':cp('opponentLevelScore',default=_v207_norm01(fit.get('level'),.5)),\n"
    "            'lap':cp('lapScore'),'jockey':cp('jockeyScore','jockeyResults'),'trainer':cp('trainerScore','trainerResults'),'body':cp('bodyWeightScore'),\n"
    "            'condition_change':cp('conditionChangeScore'),'ten':_v207_norm01(st.get('ten'),.5),'early3':_v207_norm01(st.get('early3'),0),\n"
    "            'moved3':_v207_norm01(st.get('moved3'),0),'front':_v207_norm01(st.get('front'),0),'stalk':_v207_norm01(st.get('stalk'),0),\n"
    "            'mid':_v207_norm01(st.get('mid'),0),'close':_v207_norm01(st.get('close'),0),'evidence':evidence,'data':full,\n"
    "            'recent_win':wins/used if used else .1,'recent_top3':top3/used if used else .25,'recent_avg_finish':avg,'recent_peak_finish':peak,\n"
    "            'recent_last_finish':last,'recent_gain':max(0.0,min(1.0,.5+.5*(sum(gains)/len(gains) if gains else 0.0))),\n"
    "            'recent_early':sum(earlys)/len(earlys) if earlys else .5,'recent_front_hold':sum(front_hold)/len(front_hold) if front_hold else .25,\n"
    "            'inside':1.0-(no-1)/max(1,field-1),'weight_rel':1.0-(w-wmin)/max(1e-6,wmax-wmin) if w is not None and wmax>wmin else .5,\n"
    "            'age_rel':1.0-(age-amin)/max(1e-6,amax-amin) if age is not None and amax>amin else .5,\n"
    '        }\n'
    '        rows.append(f)\n'
    "    rel_sources=['eval_score','race_perf','representative','distance','track','level','ten','early3','moved3','recent_avg_finish','recent_peak_finish','recent_top3']\n"
    '    for name in rel_sources:\n'
    '        ranks=_v213_rank_percentiles([f[name] for f in rows])\n'
    "        for i,f in enumerate(rows):f['rel_'+name]=ranks[i]\n"
    "    try:dist=float(detail.get('distance') or 1600)\n"
    '    except (TypeError,ValueError):dist=1600\n'
    '    short=max(0.0,min(1.0,(1800.0-dist)/600.0));long=max(0.0,min(1.0,(dist-1600.0)/800.0))\n'
    '    for i,f in enumerate(rows):\n'
    "        others=[z['early3'] for j,z in enumerate(rows) if j!=i];pressure=sum(others)/len(others) if others else .5;late=.42*f['moved3']+.32*f['mid']+.26*f['close']\n"
    "        f['short_ten']=short*f['ten'];f['short_early3']=short*f['early3'];f['long_late']=long*late;f['front_conflict']=f['early3']*pressure;f['lone_front']=f['early3']*(1.0-pressure);f['late_role']=late\n"
    '    return rows\n'
    '\n'
    '\n'
    '\n'
    '\n'
    'def _v215_speed_ratio(rr: dict) -> float | None:\n'
    '    try:\n'
    "        sec=float(rr.get('timeSeconds') or 0); dist=int(float(rr.get('distance') or 0))\n"
    '    except (TypeError,ValueError):\n'
    '        return None\n'
    '    if sec <= 0 or dist <= 0:return None\n'
    "    track=str(rr.get('track') or '');cond=str(rr.get('condition') or '不明');db=round(dist/200)*200\n"
    '    base=(V215_SPEED_BASE_EXACT.get(f"{track}|{dist}|{cond}") or\n'
    '          V215_SPEED_BASE_TRACK_DISTANCE.get(f"{track}|{dist}") or\n'
    '          V215_SPEED_BASE_DISTANCE_GOING.get(f"{db}|{cond}") or V215_SPEED_GLOBAL)\n'
    '    return max(.75,min(1.25,(dist/sec)/max(1e-9,float(base))))\n'
    '\n'
    '\n'
    'def _pc_live_track_speed(detail: dict) -> dict:\n'
    '    """Leakage-safe same-day track-speed variant from earlier completed races only.\n'
    '\n'
    '    Earlier winners are normalized by the historical track/distance/going baseline.\n'
    '    A recency-weighted mean is blended with the median, then shrunk by sample size and\n'
    '    cross-race dispersion so one exceptional winner cannot make the whole card "fast".\n'
    '    """\n'
    '    neutral={"version":"track-speed-v300","score":0.5,"ratio":1.0,"evidence":0.0,"completed":0,"label":"基準","dispersion":0.0,"source":"RaceDB pre-race"}\n'
    '    if not isinstance(detail,dict) or not RACEDB_PATH.exists():return neutral\n'
    '    ds=str(detail.get("date") or "");track=str(detail.get("track") or "");circuit=str(detail.get("circuit") or "")\n'
    '    surface=str(detail.get("surface") or "");race_no=int(detail.get("raceNumber") or 0)\n'
    '    if not ds or not track or race_no<=1:return neutral\n'
    '    vals=[]\n'
    '    conn=sqlite3.connect(RACEDB_PATH,timeout=.25);conn.row_factory=sqlite3.Row\n'
    '    try:\n'
    '        rows=conn.execute("SELECT race_no,payload FROM race_snapshots WHERE race_date=? AND circuit=? AND track=? AND race_no<? ORDER BY race_no",\n'
    '                          (ds,circuit,track,race_no)).fetchall()\n'
    '    except Exception:rows=[]\n'
    '    finally:conn.close()\n'
    '    try:target_dist=int(detail.get("distance") or 0)\n'
    '    except Exception:target_dist=0\n'
    '    for row in rows:\n'
    '        try:d=json.loads(row["payload"])\n'
    '        except Exception:continue\n'
    '        if surface and str(d.get("surface") or "") and str(d.get("surface") or "")!=surface:continue\n'
    '        result=d.get("result") or {}\n'
    '        if str(result.get("status") or "")!="確定":continue\n'
    '        winner=next((z for z in (result.get("finishers") or []) if isinstance(z,dict) and int(z.get("finish") or 0)==1),None)\n'
    '        if not winner:continue\n'
    '        try:sec=float(winner.get("timeSeconds") or 0);dist=int(d.get("distance") or 0);rn=int(row["race_no"] or 0)\n'
    '        except Exception:continue\n'
    '        if sec<=0 or dist<=0:continue\n'
    '        ratio=_v215_speed_ratio({"timeSeconds":sec,"distance":dist,"track":track,"condition":d.get("condition") or "不明"})\n'
    '        if ratio is None:continue\n'
    '        distance_w=1.0 if not target_dist or abs(dist-target_dist)<=300 else .72\n'
    '        recency_w=.82+.18*max(0.0,min(1.0,rn/max(1,race_no-1)))\n'
    '        vals.append((float(ratio),distance_w*recency_w))\n'
    '    if not vals:return neutral\n'
    '    den=sum(w for _,w in vals) or 1.0;mean_ratio=sum(v*w for v,w in vals)/den\n'
    '    ordered=sorted(v for v,_ in vals);m=len(ordered);median_ratio=ordered[m//2] if m%2 else (ordered[m//2-1]+ordered[m//2])/2\n'
    '    center=.58*median_ratio+.42*mean_ratio if m>=3 else mean_ratio\n'
    '    absdev=sorted(abs(v-median_ratio) for v,_ in vals);mad=absdev[len(absdev)//2] if absdev else 0.0\n'
    '    completed=len(vals);sample_evidence=min(1.0,completed/5.0);consistency=max(.25,min(1.0,1.0-mad/.035))\n'
    '    evidence=sample_evidence*consistency\n'
    '    shrink_factor=.22+.66*evidence\n'
    '    shrunk=1.0+(center-1.0)*shrink_factor\n'
    '    score=_pc_clamp(.5+(shrunk-1.0)*8.0,.20,.80)\n'
    '    label="高速" if shrunk>=1.012 else ("低速" if shrunk<=.988 else "標準")\n'
    '    return {"version":"track-speed-v300","score":round(score,4),"ratio":round(shrunk,5),"rawRatio":round(center,5),\n'
    '            "meanRatio":round(mean_ratio,5),"medianRatio":round(median_ratio,5),"dispersion":round(mad,5),\n'
    '            "evidence":round(evidence,4),"completed":completed,"label":label,"source":"RaceDB earlier-race robust variant"}\n'
    '\n'
    'def _strip_excluded(value):\n'
    '    if isinstance(value,dict):\n'
    '        return {k:_strip_excluded(v) for k,v in value.items() if str(k).lower() not in\n'
    "                {'cr','share','crscore','sharerate','training','trainingscore','trainingcomment','workouts','調教','シェア'}}\n"
    '    if isinstance(value,list): return [_strip_excluded(v) for v in value]\n'
    '    return value\n'
    '\n'
    '\n'
    'def _attach_evaluation_context(detail: dict) -> dict:\n'
    '    """One batched, date-bounded query for observed jockey/trainer/pedigree evidence."""\n'
    "    horses=detail.get('horses') or []\n"
    "    jockeys=sorted({h['jockey'] for h in horses if h.get('jockey')})\n"
    "    trainers=sorted({h['trainer'] for h in horses if h.get('trainer')})\n"
    "    sires=sorted({h['pedigree']['sire'] for h in horses if isinstance(h.get('pedigree'),dict) and h['pedigree'].get('sire')})\n"
    "    clauses=[];params=[str(detail.get('date') or _today_iso())]\n"
    '    for column,values in [(\'p.jockey\',jockeys),("json_extract(p.raw_json,\'$.trainer\')",trainers),(\'m.sire\',sires)]:\n'
    '        if values:\n'
    "            clauses.append(column+' IN ('+','.join('?' for _ in values)+')');params.extend(values)\n"
    '    if not clauses:return detail\n'
    '    conn=sqlite3.connect(RACEDB.path,timeout=3)\n'
    '    try:\n'
    "        records=conn.execute('SELECT p.raw_json,m.sire,p.horse_key,p.race_date,p.track FROM past_runs p LEFT JOIN horse_master m ON m.horse_key=p.horse_key WHERE p.race_date<? AND ('+' OR '.join(clauses)+')',params).fetchall()\n"
    '    finally:conn.close()\n'
    '    unique={}\n'
    '    for raw,sire,key,date,track in records:\n'
    '        run=json.loads(raw)\n'
    "        identity=(key,date,track,str(run.get('raceNumber') or run.get('raceId') or run.get('title') or ''))\n"
    '        unique[identity]=(run,sire)\n'
    "    jump=detail.get('analysisMode')=='障害' or _is_jump_run(detail)\n"
    '    pool=[(run,sire) for run,sire in unique.values() if _is_jump_run(run)==jump]\n'
    '    for h in horses:\n'
    "        evidence=h.setdefault('evaluationSources',{})\n"
    "        for role in ('jockey','trainer'):\n"
    "            rows=[run for run,_ in pool if h.get(role) and run.get(role)==h[role] and (_evaluation_number(run.get('finish')) or 0)>0]\n"
    "            field=('jump'+role.title() if jump else role)+'Stats'\n"
    '            old=h.get(field) or {}\n'
    "            if rows and len(rows)>int(old.get('starts') or 0):\n"
    "                h[field]={'starts':len(rows),'wins':sum(_evaluation_number(z.get('finish'))==1 for z in rows),'source':'RaceDB・対象日より前の取得済み全走'}\n"
    "                evidence[field]={'samples':len(rows),'cutoff':detail.get('date'),'scope':'障害' if jump else '平地'}\n"
    "        sire=(h.get('pedigree') or {}).get('sire')\n"
    "        offspring=[run for run,s in pool if sire and s==sire and run.get('surface')==detail.get('surface') and abs(int(run.get('distance') or 0)-int(detail.get('distance') or 0))<=200 and (_evaluation_number(run.get('finish')) or 0)>0]\n"
    "        if offspring and h.get('pedigreeScore') is None:\n"
    "            h['pedigreeScore']=sum(_evaluation_number(z.get('finish'))==1 for z in offspring)/len(offspring)\n"
    "            evidence['pedigreeScore']={'samples':len(offspring),'source':'RaceDB父産駒・同馬場・距離差200m以内勝率','cutoff':detail.get('date')}\n"
    '    return detail\n'
    '\n'
    '\n'
    'def _attach_stored_career(detail: dict) -> dict:\n'
    '    horses=detail.get("horses") or []\n'
    '    keys={RACEDB._horse_key(h):h for h in horses if RACEDB._horse_key(h)}\n'
    '    if not keys:return detail\n'
    '    conn=sqlite3.connect(RACEDB.path,timeout=3)\n'
    '    try:\n'
    '        placeholders=",".join("?" for _ in keys)\n'
    '        rows=conn.execute("SELECT horse_key,raw_json FROM past_runs WHERE horse_key IN ("+placeholders+") AND race_date<? ORDER BY race_date DESC",[*keys,str(detail.get("date") or _today_iso())]).fetchall()\n'
    '        grouped={key:{} for key in keys}\n'
    '        for key,raw in rows:\n'
    '            run=json.loads(raw);grouped[key][RACEDB._run_key(run)]=run\n'
    '        for key,horse in keys.items():\n'
    '            for run in (horse.get("allPastRuns") or horse.get("recentRaces") or []):grouped[key][RACEDB._run_key(run)]=run\n'
    '            horse["allPastRuns"]=sorted(grouped[key].values(),key=lambda x:str(x.get("date") or ""),reverse=True)\n'
    '    finally:conn.close()\n'
    '    return detail\n'
    '\n'
    '\n'
    '\n'
    'def _vol_clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:\n'
    '    try:value=float(value)\n'
    '    except Exception:return lo\n'
    '    return lo if value<lo else hi if value>hi else value\n'
    '\n'
    '\n'
    'def _race_volatility(detail: dict) -> dict:\n'
    '    """Pre-race upset model. Odds, popularity and race result are never inputs."""\n'
    '    horses=list(detail.get("horses") or [])\n'
    '    field=max(int(detail.get("fieldSize") or 0),len(horses))\n'
    '    if field < 2:\n'
    '        return {"version":VOLATILITY_ENGINE_VERSION,"ready":False,"score":None,"label":"…",\n'
    '                "method":"pre-race/no-odds","reasons":["出走データ待ち"],"oddsUsed":False}\n'
    '\n'
    '    evaluated=[];style_rows=[];low_conf=0\n'
    '    for h in horses:\n'
    '        e=h.get("integratedEvaluation") or {}\n'
    '        score=_evaluation_number(e.get("score"))\n'
    '        evidence=not bool(e.get("neutralPrior")) and (\n'
    '            int(e.get("samples") or 0)>0 or bool(e.get("components"))\n'
    '        )\n'
    '        if score is not None and evidence:\n'
    '            evaluated.append(float(score))\n'
    '            if str(e.get("confidence") or "")=="低":low_conf+=1\n'
    '        st=((h.get("precomputedMetrics") or {}).get("style") or {})\n'
    '        if int(st.get("samples") or 0)>0:\n'
    '            vals=[float(st.get(k) or 0) for k in ("front","stalk","mid","close")]\n'
    '            style_rows.append({\n'
    '                "front":vals[0],"stalk":vals[1],"mid":vals[2],"close":vals[3],\n'
    '                "early3":float(st.get("early3") or 0),\n'
    '                "ambiguity":1-max(vals) if vals else 0,\n'
    '            })\n'
    '\n'
    '    min_evidence=max(3,math.ceil(field*.45))\n'
    '    debut=str(detail.get("analysisMode") or "")=="新馬" or "新馬" in str(detail.get("title") or "")\n'
    '    ready=len(evaluated)>=min_evidence or (debut and len(evaluated)>=max(3,math.ceil(field*.35)))\n'
    '    if not ready:\n'
    '        return {\n'
    '            "version":VOLATILITY_ENGINE_VERSION,"ready":False,"score":None,"label":"…",\n'
    '            "method":"pre-race/no-odds","oddsUsed":False,\n'
    '            "coverage":{"evaluated":len(evaluated),"field":field,"styles":len(style_rows)},\n'
    '            "reasons":["評価材料を収集中"]\n'
    '        }\n'
    '\n'
    '    ranked=sorted(evaluated,reverse=True)\n'
    '    top=ranked[0];second=ranked[1] if len(ranked)>1 else top;fifth=ranked[min(4,len(ranked)-1)]\n'
    '    top2_gap=max(0.0,top-second);top5_gap=max(0.0,top-fifth)\n'
    '    parity=1-_vol_clamp(top5_gap/24.0)\n'
    '    dominance=_vol_clamp(top2_gap/12.0)\n'
    '    close_count=sum(1 for s in ranked if s>=top-8.0)\n'
    '    depth=_vol_clamp(close_count/max(2,min(field,8)))\n'
    '\n'
    '    front_count=0;closer_count=0;ambiguities=[]\n'
    '    for st in style_rows:\n'
    '        if st["early3"]>=.48 or st["front"]>=.30 or st["stalk"]>=.45:front_count+=1\n'
    '        if st["mid"]+st["close"]>=.58:closer_count+=1\n'
    '        ambiguities.append(_vol_clamp(st["ambiguity"]))\n'
    '    pressure=_vol_clamp((front_count-1)/4.0)\n'
    '    split=_vol_clamp(min(front_count,closer_count)/3.0)\n'
    '    ambiguity=sum(ambiguities)/len(ambiguities) if ambiguities else .35\n'
    '    field_factor=_vol_clamp((field-6)/10.0)\n'
    '\n'
    '    evidence_ratio=_vol_clamp(len(evaluated)/max(1,field))\n'
    '    low_ratio=low_conf/max(1,len(evaluated))\n'
    '    uncertainty=_vol_clamp(low_ratio*.70+(1-evidence_ratio)*.30)\n'
    '    if debut:uncertainty=max(uncertainty,.58)\n'
    '\n'
    '    raw=_vol_clamp(\n'
    '        .28*parity + .18*depth + .17*pressure + .12*field_factor +\n'
    '        .08*ambiguity + .07*split + .10*uncertainty - .18*dominance\n'
    '    )\n'
    '    score=max(1,min(18,1+round(raw*17)))\n'
    '    label="硬" if score<=5 else "標" if score<=10 else "荒" if score<=14 else "大荒"\n'
    '\n'
    '    signals=[\n'
    '        (parity,"上位拮抗"),(depth,"相手候補多い"),(pressure,"先行競合"),\n'
    '        (field_factor,"多頭数"),(split,"前後分断"),(uncertainty,"不確定要素")\n'
    '    ]\n'
    '    reasons=[name for value,name in sorted(signals,reverse=True) if value>=.38][:3]\n'
    '    if dominance>=.58:reasons=["上位1頭優勢"]+reasons[:2]\n'
    '    if not reasons:reasons=["標準的な構造"]\n'
    '\n'
    '    return {\n'
    '        "version":VOLATILITY_ENGINE_VERSION,"ready":True,"score":int(score),"label":label,\n'
    '        "method":"pre-race/no-odds","oddsUsed":False,"reasons":reasons[:3],\n'
    '        "coverage":{"evaluated":len(evaluated),"field":field,"styles":len(style_rows)},\n'
    '        "components":{\n'
    '            "parity":round(parity,3),"depth":round(depth,3),"frontPressure":round(pressure,3),\n'
    '            "fieldSize":round(field_factor,3),"styleAmbiguity":round(ambiguity,3),\n'
    '            "frontBackSplit":round(split,3),"uncertainty":round(uncertainty,3),\n'
    '            "topDominance":round(dominance,3)\n'
    '        }\n'
    '    }\n'
)

def install_evaluation_core(namespace: dict) -> None:
    code = compile(SOURCE, '<arvexq:evaluation_core>', 'exec')
    exec(code, namespace, namespace)

    # Do not generate or wrap a second ranking. The old code no longer exists.
    from arvexq.prediction.final_marks import apply_core_marks

    def _rank_evaluations_core_marks(detail):
        return apply_core_marks(detail)

    _rank_evaluations_core_marks._arvexq_core_marks_wrapped = True
    _rank_evaluations_core_marks.__name__ = '_rank_evaluations'
    namespace['_rank_evaluations'] = _rank_evaluations_core_marks
