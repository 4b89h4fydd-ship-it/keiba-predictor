from __future__ import annotations

# Transitional extraction of evaluation_core from app.py.
# The block is executed in the caller namespace to preserve legacy global lookup.
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
    'def _v313_same_day_mark_profile(detail: dict) -> dict:\n'
    '    """Leakage-safe same-day style + mark-miss profile from earlier finalized races only."""\n'
    '    neutral={"version":"sameday-mark-v316","active":False,"completed":0,"evidence":0.0,"coverage":1.0,"deficit":0.0,\n'
    '             "frontSignal":0.0,"lateSignal":0.0,"innerSignal":0.0,"flowLabel":"中立","sourceRaces":[]}\n'
    '    if not isinstance(detail,dict) or not RACEDB_PATH.exists():return neutral\n'
    '    ds=str(detail.get("date") or "");track=str(detail.get("track") or "");circuit=str(detail.get("circuit") or "")\n'
    '    try:race_no=int(detail.get("raceNumber") or 0)\n'
    '    except Exception:race_no=0\n'
    '    if not ds or not track or race_no<=1:return neutral\n'
    '    conn=sqlite3.connect(RACEDB_PATH,timeout=.25);conn.row_factory=sqlite3.Row\n'
    '    try:\n'
    '        rows=conn.execute("SELECT race_no,payload FROM race_snapshots WHERE race_date=? AND circuit=? AND track=? AND race_no<? ORDER BY race_no",\n'
    '                          (ds,circuit,track,race_no)).fetchall()\n'
    '    except Exception:rows=[]\n'
    '    finally:conn.close()\n'
    '    completed=mark_races=full_hit=style_n=pod_front=pod_late=miss_n=miss_front=miss_late=frame_n=0;inner=0.0;source=[]\n'
    '    valid_marks={"◎","○","▲","☆+","☆","△","注+","注"}\n'
    '    for row in rows:\n'
    '        try:d=json.loads(row["payload"])\n'
    '        except Exception:continue\n'
    '        result=d.get("result") if isinstance(d.get("result"),dict) else {}\n'
    '        if str(result.get("status") or "")!="確定":continue\n'
    '        fs=[x for x in (result.get("finishers") or []) if isinstance(x,dict) and int(x.get("finish") or 0)>0]\n'
    '        fs.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)));fs=fs[:3]\n'
    '        if len(fs)<3:continue\n'
    '        completed+=1;source.append(int(row["race_no"] or 0))\n'
    '        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else {}\n'
    '        locked=lock.get("horses") if isinstance(lock.get("horses"),list) else []\n'
    '        # Mark-miss learning is valid only when the earlier race has an immutable\n'
    '        # pre-race lock. Historical post-race/recomputed marks must never substitute.\n'
    '        marked={int(x.get("horseNumber") or 0) for x in locked if isinstance(x,dict) and str(x.get("mark") or "") in valid_marks}\n'
    '        comparable=bool(marked)\n'
    '        if comparable:\n'
    '            mark_races+=1\n'
    '            if all(int(f.get("horseNumber") or 0) in marked for f in fs):full_hit+=1\n'
    '        field=max(1,int(d.get("fieldSize") or len(d.get("horses") or []) or len(fs)));front_cut=max(2,math.ceil(field*.25));late_cut=max(front_cut+1,math.ceil(field*.55))\n'
    '        by_no={int(h.get("horseNumber") or 0):h for h in (d.get("horses") or []) if isinstance(h,dict)}\n'
    '        for f in fs:\n'
    '            cp=[int(v) for v in (f.get("cornerPositions") or []) if str(v).isdigit() and int(v)>0];pos=cp[0] if cp else 0\n'
    '            is_front=bool(pos and pos<=front_cut);is_late=bool(pos and pos>=late_cut)\n'
    '            if pos:\n'
    '                style_n+=1;pod_front+=1 if is_front else 0;pod_late+=1 if is_late else 0\n'
    '            h=by_no.get(int(f.get("horseNumber") or 0),{});fr=int(f.get("frameNumber") or h.get("frameNumber") or 0)\n'
    '            if fr>0:\n'
    '                frame_n+=1;max_frame=max(2,min(8,math.ceil(field/2)));inside=max(0.0,min(1.0,1-(fr-1)/max(1,max_frame-1)));inner+=inside\n'
    '            if comparable and int(f.get("horseNumber") or 0) not in marked:\n'
    '                miss_n+=1;miss_front+=1 if is_front else 0;miss_late+=1 if is_late else 0\n'
    '    if completed<2:return dict(neutral,completed=completed,sourceRaces=source)\n'
    '    clampf=lambda x,lo=0.0,hi=1.0:max(lo,min(hi,float(x)))\n'
    '    sample=clampf((completed-1)/4);coverage=(full_hit/mark_races) if mark_races else .83;deficit=clampf((.83-coverage)/.50) if mark_races else 0.0\n'
    '    front_share=pod_front/style_n if style_n else .34;late_share=pod_late/style_n if style_n else .26;inner_share=inner/frame_n if frame_n else .5\n'
    '    miss_front_share=miss_front/miss_n if miss_n else .33;miss_late_share=miss_late/miss_n if miss_n else .33\n'
    '    evidence=clampf(sample*(.62+.38*min(1,style_n/9))*(.72+.28*min(1,completed/4)))\n'
    '    front_signal=clampf(((front_share-.34)*2.15+(miss_front_share-.33)*deficit*.80),-.42,.42)*evidence\n'
    '    late_signal=clampf(((late_share-.26)*2.30+(miss_late_share-.33)*deficit*.88),-.42,.42)*evidence\n'
    '    inner_signal=clampf((inner_share-.5)*1.65,-.30,.30)*evidence\n'
    '    if late_signal>=.055 and late_signal>=abs(front_signal)*.85:flow="差し・追込"\n'
    '    elif front_signal>=.055 and front_signal>=abs(late_signal)*.85:flow="前残り"\n'
    '    elif front_signal<=-.055:flow="前不利"\n'
    '    else:flow="差し不利" if late_signal<=-.055 else ""\n'
    '    if not flow and abs(inner_signal)>=.06:flow="内寄り" if inner_signal>0 else "外寄り"\n'
    '    return {"version":"sameday-mark-v316","active":bool(evidence>=.18),"completed":completed,"markRaces":mark_races,"evidence":round(evidence,6),"coverage":round(coverage,6),\n'
    '            "deficit":round(deficit,6),"frontSignal":round(front_signal,6),"lateSignal":round(late_signal,6),"innerSignal":round(inner_signal,6),\n'
    '            "flowLabel":flow or "中立","sourceRaces":source}\n'
    '\n'
    'def _v313_horse_flow_adjust(h:dict, profile:dict, field:int)->float:\n'
    '    if not profile or not profile.get("active"):return 0.0\n'
    '    runs=list(h.get("recentRaces") or h.get("allPastRuns") or [])[:5];early=late=den=0.0\n'
    '    for j,rr in enumerate(runs):\n'
    '        if not isinstance(rr,dict):continue\n'
    '        cp=[]\n'
    '        for v in (rr.get("cornerPositions") or []):\n'
    '            try:q=int(v)\n'
    '            except Exception:q=0\n'
    '            if q>0:cp.append(q)\n'
    '        if not cp:continue\n'
    '        try:fs=max(4,int(rr.get("fieldSize") or 12))\n'
    '        except Exception:fs=12\n'
    '        w=.78**j;pos=cp[0];norm=(pos-1)/max(3,fs-1);den+=w\n'
    '        if pos<=max(2,math.ceil(fs*.25)):early+=w\n'
    '        elif norm>=.55:late+=w\n'
    '        if len(cp)>1 and cp[-1]<=max(3,math.ceil(fs*.30)) and pos>max(3,math.ceil(fs*.30)):late+=w*.35\n'
    '    if den<=0:early=late=.5\n'
    '    else:early/=den;late=min(1.0,late/den)\n'
    '    try:fr=int(h.get("frameNumber") or 0)\n'
    '    except Exception:fr=0\n'
    '    max_frame=max(2,min(8,math.ceil(max(2,field)/2)));inside=max(0.0,min(1.0,1-(fr-1)/max(1,max_frame-1))) if fr else .5\n'
    '    raw=float(profile.get("frontSignal") or 0)*(early-late)+float(profile.get("lateSignal") or 0)*(late-early)+float(profile.get("innerSignal") or 0)*(inside-.5)*1.35\n'
    '    return max(-.06,min(.06,raw))\n'
    '\n'
    'def _v215_draw_score(track: str, dist: int, group: int) -> float:\n'
    '    db=round(int(dist or 0)/200)*200\n'
    '    arr=V215_DRAW_STATS.get(f"{track}|{db}")\n'
    '    if not arr or sum(arr[:3]) < 24:arr=V215_TRACK_DRAW_STATS.get(str(track))\n'
    '    if not arr or sum(arr[:3]) < 20:return .5\n'
    '    starts=float(arr[group]);hits=float(arr[3+group]);total_s=float(sum(arr[:3]));total_h=float(sum(arr[3:]))\n'
    '    base=(total_h+3)/(total_s+9);rate=(hits+1)/(starts+3);lift=rate/max(.05,base)\n'
    '    return max(0.0,min(1.0,.5+.45*(lift-1)))\n'
    '\n'
    '\n'
    'def _v215_prof_feature_rows(detail: dict, horses: list[dict], base_rows: list[dict]) -> list[dict]:\n'
    '    rows=[];field=max(1,len(horses))\n'
    "    try:target_date=dt_date.fromisoformat(str(detail.get('date') or ''))\n"
    '    except Exception:target_date=None\n'
    '    for idx,h in enumerate(horses):\n'
    "        f=dict(base_rows[idx]);runs=list(h.get('recentRaces') or [])[:5]\n"
    '        finish_scores=[];wf_num=wf_den=0.0;speed_vals=[];speed_ws=[];carried=[];prizes=[];days=[]\n'
    '        for j,rr in enumerate(runs):\n'
    '            wrec=.72**j\n'
    "            try:fin=int(float(rr.get('finish') or rr.get('finishPosition') or 0))\n"
    '            except (TypeError,ValueError):fin=0\n'
    "            try:fs=max(2,int(float(rr.get('fieldSize') or 12)))\n"
    '            except (TypeError,ValueError):fs=12\n'
    '            if fin>0:\n'
    '                score=max(0.0,min(1.0,1.0-(fin-1)/max(1,fs-1)));finish_scores.append(score);wf_num+=score*wrec;wf_den+=wrec\n'
    '            sr=_v215_speed_ratio(rr)\n'
    '            if sr is not None:speed_vals.append(sr);speed_ws.append(wrec)\n'
    '            try:\n'
    "                cw=float(rr.get('carriedWeight'))\n"
    '                if math.isfinite(cw):carried.append(cw)\n'
    '            except (TypeError,ValueError):pass\n'
    '            try:\n'
    "                rp=float(rr.get('racePrize1') or 0)\n"
    '                if rp>0:prizes.append(rp)\n'
    '            except (TypeError,ValueError):pass\n'
    "            if target_date and rr.get('date'):\n"
    "                try:days.append(max(0,(target_date-dt_date.fromisoformat(str(rr.get('date')))).days))\n"
    '                except Exception:pass\n'
    '        trend=(finish_scores[0]-(sum(finish_scores[1:])/len(finish_scores[1:]) if len(finish_scores)>1 else finish_scores[0])) if finish_scores else 0.0\n'
    '        spavg=sum(v*w for v,w in zip(speed_vals,speed_ws))/sum(speed_ws) if speed_vals else 1.0\n'
    '        spbest=max(speed_vals) if speed_vals else 1.0;splast=speed_vals[0] if speed_vals else 1.0\n'
    '        sptrend=(speed_vals[0]-(sum(speed_vals[1:])/len(speed_vals[1:]) if len(speed_vals)>1 else speed_vals[0])) if speed_vals else 0.0\n'
    "        curpr=float(detail.get('racePrize1') or 0);prevpr=(sum(prizes)/len(prizes) if prizes else 0.0);bestpr=max(prizes) if prizes else 0.0\n"
    '        class_drop=.5 if curpr<=0 or prevpr<=0 else max(0.0,min(1.0,.5+.22*math.log(max(1e-6,prevpr/curpr))))\n'
    '        class_fit=.5 if curpr<=0 or bestpr<=0 else max(0.0,min(1.0,.5+.20*math.log(max(1e-6,bestpr/curpr))))\n'
    "        try:curw=float(h.get('carriedWeight'));curw=curw if math.isfinite(curw) else float('nan')\n"
    "        except (TypeError,ValueError):curw=float('nan')\n"
    '        lastw=carried[0] if carried else curw\n'
    '        wd=0.0 if not (math.isfinite(curw) and math.isfinite(lastw)) else curw-lastw\n'
    '        weight_delta=max(0.0,min(1.0,.5-.08*wd));wstd=float(np.std(carried)) if False else (math.sqrt(sum((x-sum(carried)/len(carried))**2 for x in carried)/len(carried)) if len(carried)>=2 else 0.0)\n'
    "        jp=h.get('jockeyProfile') or {};tp=h.get('trainerProfile') or {}\n"
    '        def pv(p,key,default=.5):return _v207_norm01(p.get(key),default)\n'
    "        jctx=sum(pv(jp,k) for k in ('overall','track','distance','condition'))/4.0;tctx=sum(pv(tp,k) for k in ('overall','track','distance','condition'))/4.0\n"
    "        no=int(h.get('horseNumber') or 0);q=(no-1)/max(1,field-1);grp=0 if q<.34 else (2 if q>.66 else 1)\n"
    '        f.update({\n'
    "            'speed_adj_avg':max(0.0,min(1.0,.5+(spavg-1)*3.2)),'speed_adj_best':max(0.0,min(1.0,.5+(spbest-1)*2.8)),\n"
    "            'speed_adj_last':max(0.0,min(1.0,.5+(splast-1)*3.0)),'speed_adj_trend':max(0.0,min(1.0,.5+sptrend*5)),\n"
    "            'speed_evidence':min(1.0,len(speed_vals)/5.0),'recency_wfinish':wf_num/wf_den if wf_den else .5,\n"
    "            'finish_trend':max(0.0,min(1.0,.5+trend*.8)),'days_since_last':min(1.0,(days[0] if days else 90)/180.0),\n"
    "            'freshness':max(0.0,min(1.0,1-abs((days[0] if days else 45)-28)/120.0)),'class_drop':class_drop,'class_fit':class_fit,\n"
    "            'weight_delta':weight_delta,'weight_stability':max(0.0,min(1.0,1-wstd/4.0)),'jockey_ctx':jctx,'jockey_track':pv(jp,'track'),\n"
    "            'jockey_distance':pv(jp,'distance'),'jockey_condition':pv(jp,'condition'),'jockey_front':pv(jp,'early3Rate'),\n"
    "            'trainer_ctx':tctx,'trainer_track':pv(tp,'track'),'trainer_distance':pv(tp,'distance'),'trainer_condition':pv(tp,'condition'),\n"
    "            'draw_hist':_v215_draw_score(str(detail.get('track') or ''),int(float(detail.get('distance') or 1600)),grp),\n"
    "            'live_draw':.5,'live_style':.5,'field_norm':max(0.0,min(1.0,(field-4)/12.0)),\n"
    "            'style_reliability':min(1.0,max(int((h.get('precomputedMetrics') or {}).get('style',{}).get('samples') or 0),int((h.get('integratedEvaluation') or {}).get('samples') or 0))/5.0),\n"
    '        })\n'
    '        rows.append(f)\n'
    '    for i,f in enumerate(rows):\n'
    "        others=[z.get('early3',0) for j,z in enumerate(rows) if j!=i];pressure=sum(others)/len(others) if others else .5\n"
    "        late=.42*f.get('moved3',0)+.32*f.get('mid',0)+.26*f.get('close',0);early=max(f.get('front',0),f.get('stalk',0),f.get('early3',0))\n"
    "        f['pace_fit']=max(0.0,min(1.0,early*(1-pressure)+late*pressure))\n"
    '    return rows\n'
    '\n'
    '\n'
    'def _v215_professional_p1(detail: dict, horses: list[dict], base_rows: list[dict]) -> list[float]:\n'
    '    feats=_v215_prof_feature_rows(detail,horses,base_rows);raw=[]\n'
    '    for f in feats:\n'
    '        total=0.0\n'
    '        for i,name in enumerate(V215_FEATURES):\n'
    '            total += V215_P1_COEF[i]*((f.get(name,.5)-V215_MEAN[i])/max(1e-9,V215_SCALE[i]))\n'
    '        raw.append(total)\n'
    '    return _v213_zscore(raw)\n'
    '\n'
    '# v218 tactical + conditional-role bridge.\n'
    '# v215/v213 remain the statistical bases. v218 strengthens the race-reading layer\n'
    '# using TRUE RUN, individual neighbour pressure, a probability mixture of pace shapes,\n'
    '# and role-specific compatibility. It does not use post-race information.\n'
    'V218_TACTICAL_MODEL_VERSION = "arvexq-seven-axis-overlay-v239"\n'
    'V218_P1_BLEND = 0.24\n'
    '\n'
    '\n'
    'def _v218_tactical_roles(detail: dict, horses: list[dict], base_rows: list[dict]):\n'
    '    feats=_v215_prof_feature_rows(detail,horses,base_rows)\n'
    '    field=max(1,len(feats))\n'
    "    order=sorted(range(len(horses)), key=lambda i:int(horses[i].get('horseNumber') or i+1))\n"
    "    early=[max(float(f.get('front',0)),float(f.get('stalk',0)),float(f.get('early3',0))) for f in feats]\n"
    '    pressure=max(0.0,min(1.0,(sum(early)/field)*1.45))\n'
    '    front_count=sum(1 for v in early if v>=.48)\n'
    "    late_count=sum(1 for f in feats if float(f.get('late_role',0))>=.48)\n"
    "    track_speed=detail.get('trackSpeed') or {}\n"
    "    track_speed_score=max(0.0,min(1.0,float(track_speed.get('score') or .5)))\n"
    "    track_speed_evidence=max(0.0,min(1.0,float(track_speed.get('evidence') or 0)))\n"
    '\n'
    '    # Build multiple plausible race shapes instead of forcing one deterministic pace call.\n'
    '    front_prob=max(.08,min(.58,.16+(1-pressure)*.24+(.10 if front_count==1 else 0.0)))\n'
    '    collapse_prob=max(.08,min(.58,.10+pressure*.34+max(0,front_count-2)*.035))\n'
    '    late_prob=max(.08,min(.34,.10+(late_count/field)*.16+pressure*.08))\n'
    '    neutral_prob=max(.08,1.0-front_prob-collapse_prob-late_prob)\n'
    '    psum=front_prob+collapse_prob+late_prob+neutral_prob\n'
    '    front_prob/=psum;collapse_prob/=psum;late_prob/=psum;neutral_prob/=psum\n'
    '\n'
    '    # Individual neighbour pressure by horse-number adjacency. This is deliberately\n'
    '    # separate from overall pace pressure: a front horse can face a hard local squeeze\n'
    '    # even in a race that is not globally extreme.\n'
    "    neighbour=[{'left':0.0,'right':0.0,'sandwich':0.0,'local':0.0} for _ in feats]\n"
    '    for pos,idx in enumerate(order):\n'
    '        left=early[order[pos-1]] if pos>0 else 0.0\n'
    '        right=early[order[pos+1]] if pos+1<len(order) else 0.0\n'
    '        sandwich=1.0 if left>=.52 and right>=.52 else 0.0\n'
    '        local=max(left,right,.5*(left+right))\n'
    "        neighbour[idx]={'left':left,'right':right,'sandwich':sandwich,'local':local}\n"
    '\n'
    '    p1_raw=[];p2_role=[];p3_role=[];audits=[]\n'
    '    for i,f in enumerate(feats):\n'
    '        nb=neighbour[i]\n'
    '        pure=max(0.0,min(1.0,\n'
    "            .24*f.get('eval_score',.5)+.18*f.get('race_perf',.5)+.16*f.get('representative',.5)+\n"
    "            .10*f.get('level',.5)+.08*f.get('distance',.5)+.07*f.get('track',.5)+\n"
    "            .06*f.get('going',.5)+.06*f.get('lap',.5)+.05*f.get('evidence',.5)\n"
    '        ))\n'
    '\n'
    '        # TRUE RUN approximates the performance hidden by finishing position. Early\n'
    '        # effort, mid-race gain and adjusted speed can rescue a superficially poor run;\n'
    '        # easy-front/conflict-free trips get less credit.\n'
    "        effort_gap=f.get('recent_early',.5)-f.get('recent_last_finish',.5)\n"
    "        gain=f.get('recent_gain',.5)-.5\n"
    "        local_cost=max(0.0,min(1.0,.62*nb['local']+.38*nb['sandwich']))\n"
    "        hidden=max(0.0,min(1.0,.50+.55*effort_gap+.25*gain-.15*f.get('lone_front',0)+.14*local_cost))\n"
    '        true_run=max(0.0,min(1.0,\n'
    "            .22*f.get('speed_adj_avg',.5)+.16*f.get('speed_adj_best',.5)+\n"
    "            .15*f.get('speed_adj_last',.5)+.14*f.get('recency_wfinish',.5)+\n"
    "            .10*f.get('finish_trend',.5)+.13*hidden+.10*f.get('class_fit',.5)\n"
    '        ))\n'
    '\n'
    '        # v300 robust live track-speed fit. A fast surface rewards horses that can sustain\n'
    '        # raw speed/early position; a slow surface rewards TRUE RUN, late role and\n'
    '        # going tolerance. Evidence controls the strength and neutralizes early races.\n'
    "        fast_track_fit=max(0.0,min(1.0,.42*f.get('speed_adj_best',.5)+.28*f.get('speed_adj_avg',.5)+.18*f.get('ten',.5)+.12*f.get('early3',0)))\n"
    "        slow_track_fit=max(0.0,min(1.0,.36*true_run+.27*f.get('late_role',0)+.21*f.get('going',.5)+.16*f.get('class_fit',.5)))\n"
    '        if track_speed_score>=.52:track_speed_fit=fast_track_fit\n'
    '        elif track_speed_score<=.48:track_speed_fit=slow_track_fit\n'
    '        else:track_speed_fit=.5*(fast_track_fit+slow_track_fit)\n'
    '        track_speed_intensity=min(1.0,abs(track_speed_score-.5)*2.0)*track_speed_evidence\n'
    '        track_speed_fit=.5+(track_speed_fit-.5)*track_speed_intensity\n'
    '\n'
    '        front_fit=max(0.0,min(1.0,\n'
    "            .29*f.get('lone_front',0)+.23*f.get('recent_front_hold',.25)+\n"
    "            .19*f.get('early3',0)+.13*f.get('ten',.5)+.10*(1-f.get('front_conflict',0))+\n"
    '            .06*(1-local_cost)\n'
    '        ))\n'
    '        collapse_fit=max(0.0,min(1.0,\n'
    "            .31*f.get('late_role',0)+.21*f.get('moved3',0)+.17*f.get('recent_gain',.5)+\n"
    "            .13*f.get('close',0)+.11*f.get('speed_adj_best',.5)+.07*local_cost\n"
    '        ))\n'
    '        late_fit=max(0.0,min(1.0,\n'
    "            .28*f.get('late_role',0)+.23*f.get('mid',0)+.19*f.get('close',0)+\n"
    "            .15*f.get('finish_trend',.5)+.10*f.get('speed_adj_avg',.5)+.05*true_run\n"
    '        ))\n'
    "        neutral_fit=max(0.0,min(1.0,.55*pure+.23*f.get('pace_fit',.5)+.22*true_run))\n"
    '        scenario=max(0.0,min(1.0,\n'
    '            front_prob*front_fit+collapse_prob*collapse_fit+late_prob*late_fit+neutral_prob*neutral_fit\n'
    '        ))\n'
    '        scenario=max(0.0,min(1.0,scenario*(1-.04*track_speed_evidence)+track_speed_fit*(.04*track_speed_evidence)))\n'
    '\n'
    '        # v238: "今回条件" is deliberately stronger, with more weight on the\n'
    '        # race-specific facts (distance/course/going/class/draw) and less on\n'
    '        # generic connections.  This is still bounded and evidence-regularized\n'
    '        # downstream so one noisy condition cannot dominate the whole forecast.\n'
    '        conditions=max(0.0,min(1.0,\n'
    "            .18*f.get('distance',.5)+.15*f.get('track',.5)+.15*f.get('going',.5)+\n"
    "            .14*f.get('class_fit',.5)+.10*f.get('draw_hist',.5)+.08*f.get('jockey_ctx',.5)+\n"
    "            .06*f.get('trainer_ctx',.5)+.05*f.get('freshness',.5)+.04*f.get('weight_delta',.5)+\n"
    "            .05*f.get('pace_fit',.5)\n"
    '        ))\n'
    '        conditions=max(0.0,min(1.0,conditions*(1-.06*track_speed_evidence)+track_speed_fit*(.06*track_speed_evidence)))\n'
    "        evidence=max(0.0,min(1.0,.62*f.get('evidence',.5)+.38*f.get('style_reliability',.5)))\n"
    '\n'
    '        # v239 seven-axis ability model.  The visible detail screen is intentionally\n'
    '        # simple, but prediction keeps the full internal split: PURE / TRUE RUN /\n'
    '        # SECTIONAL / pace fit / current conditions / opponent level / reproducibility.\n'
    '        sectional=max(0.0,min(1.0,\n'
    "            .55*f.get('lap',.5)+.25*f.get('speed_adj_avg',.5)+.20*f.get('speed_adj_best',.5)\n"
    '        ))\n'
    "        opponent=max(0.0,min(1.0,.62*f.get('level',.5)+.38*f.get('class_fit',.5)))\n"
    '        reproducibility=max(0.0,min(1.0,\n'
    "            .30*evidence+.18*f.get('recency_wfinish',.5)+.14*f.get('finish_trend',.5)+\n"
    "            .14*f.get('weight_stability',.5)+.12*f.get('style_reliability',.5)+\n"
    "            .12*f.get('speed_evidence',.5)\n"
    '        ))\n'
    "        # Keep the user's strengthened current-condition stance (22%) while\n"
    '        # separating the other six concepts instead of hiding them inside one score.\n'
    '        p1_score=(.21*pure+.17*true_run+.12*sectional+.14*scenario+.22*conditions+\n'
    '                  .08*opponent+.06*reproducibility)\n'
    '        p1_score=.5+(p1_score-.5)*(.58+.42*evidence)\n'
    '        p1_raw.append(p1_score)\n'
    '\n'
    '        # Role compatibility is not a replacement for the validated P2/P3 marginal\n'
    '        # models. It is emitted for the conditional-order engine to use after a winner\n'
    '        # or winner+runner-up has been fixed.\n'
    '        second=max(0.0,min(1.0,\n'
    "            .23*true_run+.22*f.get('pace_fit',.5)+.18*f.get('recent_front_hold',.5)+\n"
    "            .15*f.get('moved3',.5)+.12*conditions+.10*(1-.55*local_cost)\n"
    '        ))\n'
    '        third=max(0.0,min(1.0,\n'
    "            .22*true_run+.21*f.get('late_role',.5)+.17*f.get('moved3',.5)+\n"
    "            .14*f.get('close',.5)+.14*conditions+.12*evidence\n"
    '        ))\n'
    '        p2_role.append(second);p3_role.append(third)\n'
    '        audits.append({\n'
    "            'pure':round(pure,4),'trueRun':round(true_run,4),'hiddenEffort':round(hidden,4),\n"
    "            'sectional':round(sectional,4),'positionScenario':round(scenario,4),'conditions':round(conditions,4),\n"
    "            'opponentLevel':round(opponent,4),'stateConsistency':round(reproducibility,4),'sevenAxisScore':round(p1_score,4),\n"
    "            'trackSpeedFit':round(track_speed_fit,4),'trackSpeed':{'score':round(track_speed_score,4),'evidence':round(track_speed_evidence,4),'ratio':track_speed.get('ratio',1.0),'label':track_speed.get('label','基準'),'completed':track_speed.get('completed',0)},\n"
    "            'secondRole':round(second,4),'thirdRole':round(third,4),'evidence':round(evidence,4),\n"
    "            'positionPressure':{\n"
    "                'left':round(nb['left'],4),'right':round(nb['right'],4),\n"
    "                'local':round(nb['local'],4),'sandwich':bool(nb['sandwich'])\n"
    '            },\n'
    "            'scenarioProbabilities':{\n"
    "                'front':round(front_prob,4),'neutral':round(neutral_prob,4),\n"
    "                'collapse':round(collapse_prob,4),'late':round(late_prob,4)\n"
    '            }\n'
    '        })\n'
    '    return _v213_zscore(p1_raw),p2_role,p3_role,audits\n'
    '\n'
    '\n'
    'def _v213_role_utilities(detail: dict, horses: list[dict]):\n'
    '    feats=_v213_feature_rows(detail,horses)\n'
    '    def linear(f,coef):\n'
    '        total=0.0\n'
    '        for i,name in enumerate(V213_FEATURES):total += coef[i]*((f.get(name,.5)-V213_MEAN[i])/max(1e-9,V213_SCALE[i]))\n'
    '        return total\n'
    '    new1=[linear(f,V213_P1_COEF) for f in feats];new2=[linear(f,V213_P2_COEF) for f in feats];new3=[linear(f,V213_P3_COEF) for f in feats]\n'
    '    cur2=[];cur3=[]\n'
    '    for f in feats:\n'
    "        p2f={'base':f['eval_score'],'perf':f['race_perf'],'rep':f['representative'],'dist':f['distance'],'track':f['track'],'going':f['going'],'level':f['level'],'jockey':f['jockey'],'trainer':f['trainer'],'body':f['body'],'lap':f['lap'],'ten':f['ten'],'early3':f['early3'],'moved3':f['moved3'],'front':f['front'],'stalk':f['stalk'],'mid':f['mid'],'close':f['close'],'evidence':f['evidence'],'data':f['data']}\n"
    '        cur2.append(V212_P2_MODEL_INTERCEPT+sum(V212_P2_MODEL_COEFFICIENTS[k]*p2f[k] for k in V212_P2_MODEL_COEFFICIENTS))\n'
    "        cur3.append(f['eval_score']*.14+f['race_perf']*.14+f['representative']*.14+f['distance']*.06+f['track']*.05+f['level']*.05+f['going']*.04+f['moved3']*.10+f['mid']*.07+f['close']*.08+f['lap']*.06+f['evidence']*.07)\n"
    '    z1=_v213_zscore(new1);z2n=_v213_zscore(new2);z2c=_v213_zscore(cur2);z3n=_v213_zscore(new3);z3c=_v213_zscore(cur3)\n'
    '    pro1=_v215_professional_p1(detail,horses,feats)\n'
    '    v215_u1=[(1.0-V215_P1_BLEND)*z1[i]+V215_P1_BLEND*pro1[i] for i in range(len(horses))]\n'
    '    tactical1,p2_role,p3_role,tactical_audit=_v218_tactical_roles(detail,horses,feats)\n'
    '    u1=[(1.0-V218_P1_BLEND)*v215_u1[i]+V218_P1_BLEND*tactical1[i] for i in range(len(horses))]\n'
    '    # Keep the validated v213 P2/P3 marginals untouched. v218 uses role compatibility\n'
    '    # conditionally in the trifecta order engine rather than silently replacing them.\n'
    '    u2=[(1.0-V213_BLEND[1])*z2c[i]+V213_BLEND[1]*z2n[i] for i in range(len(horses))]\n'
    '    u3=[(1.0-V213_BLEND[2])*z3c[i]+V213_BLEND[2]*z3n[i] for i in range(len(horses))]\n'
    '    return u1,u2,u3,_v213_softmax(u1),_v213_softmax(u2),_v213_softmax(u3),z1,pro1,tactical1,p2_role,p3_role,tactical_audit\n'
    '\n'
    'def _v317_factor_weights(detail:dict, sparse:bool=False)->dict[str,float]:\n'
    "    central=str(detail.get('circuit') or '')=='中央'\n"
    '    if central:\n'
    "        w={'ability':.12,'classLevel':.06,'form':.07,'pace':.14,'suitability':.23,'connections':.18,'pedigree':.20} if sparse else {'ability':.26,'classLevel':.12,'form':.14,'pace':.18,'suitability':.16,'connections':.08,'pedigree':.06}\n"
    '    else:\n'
    "        w={'ability':.10,'classLevel':.06,'form':.07,'pace':.18,'suitability':.25,'connections':.20,'pedigree':.14} if sparse else {'ability':.24,'classLevel':.08,'form':.16,'pace':.20,'suitability':.18,'connections':.09,'pedigree':.05}\n"
    '    def shift(a,b,x):w[a]+=x;w[b]-=x\n'
    "    try:dist=float(detail.get('distance') or 0)\n"
    '    except Exception:dist=0\n'
    "    surface=str(detail.get('surface') or '')\n"
    "    if dist and dist<=1400:shift('pace','pedigree',.025);shift('ability','classLevel',.015)\n"
    "    elif dist>=2300:shift('suitability','pace',.030);shift('classLevel','form',.015)\n"
    "    if 'ダ' in surface:shift('pace','pedigree',.020);shift('suitability','ability',.015)\n"
    "    if not central:shift('pace','classLevel',.015);shift('suitability','pedigree',.010)\n"
    '    total=sum(max(.01,v) for v in w.values()) or 1.0\n'
    '    return {k:max(.01,v)/total for k,v in w.items()}\n'
    '\n'
    '\n'
    'def _v317_factor_profile(detail:dict, horse:dict)->dict:\n'
    "    e=horse.get('integratedEvaluation') or {};c=e.get('components') if isinstance(e.get('components'),dict) else {};a=e.get('v218Audit') or e.get('v217Audit') or {};pm=horse.get('precomputedMetrics') or {};fit=pm.get('fit') or {};st=pm.get('style') or {}\n"
    '    def u(v,default=.5):\n'
    '        try:\n'
    '            x=float(v)\n'
    '            if not math.isfinite(x):return default\n'
    '            if x>1.5:x/=100.0\n'
    '            return max(0.0,min(1.0,x))\n'
    '        except Exception:return default\n'
    '    def ax(key,default=.5):return u(a.get(key),default)\n'
    '    def comp(names,default=.5):\n'
    '        for k in names:\n'
    '            if c.get(k) is not None:return u(c.get(k),default)\n'
    '        return u(default,.5)\n'
    "    runs=(horse.get('recentRaces') or horse.get('allPastRuns') or [])[:5];tot=good=0\n"
    '    for rr in runs:\n'
    '        if not isinstance(rr,dict):continue\n'
    "        try:f=int(rr.get('finish') or rr.get('finishPosition') or rr.get('rank') or 0)\n"
    '        except Exception:f=0\n'
    '        if f>0:tot+=1;good+=1 if f<=3 else 0\n'
    '    recent=good/tot if tot else .5\n'
    "    pp=a.get('positionPressure') if isinstance(a.get('positionPressure'),dict) else {}\n"
    "    frag=u(pp.get('local'),0)\n"
    "    pure=ax('pure',u(e.get('score'),.5));tr=ax('trueRun',.5);sec=ax('sectional',comp(['lapScore'],.5));scen=ax('positionScenario',.5);cond=ax('conditions',.5);opp=ax('opponentLevel',comp(['opponentLevelScore'],u(fit.get('level'),.5)));state=ax('stateConsistency',.5)\n"
    "    perf=comp(['racePerformance'],.5);rep=comp(['representative'],.5);course=comp(['courseFit'],u(fit.get('track'),.5));dist=comp(['distanceFit'],u(fit.get('distance'),.5));going=comp(['goingFit'],u(fit.get('condition'),.5));level=comp(['opponentLevelScore'],opp);lap=comp(['lapScore'],sec)\n"
    "    jockey=comp(['jockeyScore','jockeyResults'],.5);trainer=comp(['trainerScore','trainerResults'],.5);body=comp(['bodyWeightScore'],.5);change=comp(['conditionChangeScore'],.5);ped=comp(['pedigreeScore'],.5);ds=comp(['distanceSuitabilityScore'],dist);ss=comp(['surfaceSuitabilityScore'],.5);draw=comp(['drawScore'],.5)\n"
    "    ten=u(st.get('ten'),.5);moved=u(st.get('moved3'),.0);close=u(st.get('close'),.0);pace_extra=.55*ten+.25*moved+.20*close\n"
    '    ability=max(0,min(1,.28*pure+.27*tr+.17*sec+.16*perf+.12*rep))\n'
    "    class_level=max(0,min(1,.46*opp+.26*level+.16*u(fit.get('level'),.5)+.12*perf))\n"
    '    form=max(0,min(1,.30*state+.26*recent+.24*perf+.12*rep+.08*(1-frag)))\n'
    '    pace=max(0,min(1,.36*scen+.18*lap+.18*pace_extra+.15*state+.13*(1-frag)))\n'
    "    suitability=max(0,min(1,.16*cond+.17*course+.17*dist+.13*going+.12*ds+.09*ss+.08*draw+.08*u(fit.get('track'),.5)))\n"
    '    connections=max(0,min(1,.33*jockey+.25*trainer+.19*body+.15*change+.08*state))\n'
    '    pedigree=max(0,min(1,.52*ped+.28*ds+.20*ss))\n'
    "    sparse=bool(e.get('neutralPrior')) or int(e.get('samples') or 0)<2\n"
    "    weights=_v317_factor_weights(detail,sparse);factors={'ability':ability,'classLevel':class_level,'form':form,'pace':pace,'suitability':suitability,'connections':connections,'pedigree':pedigree}\n"
    "    score=sum(weights[k]*factors[k] for k in weights);central=str(detail.get('circuit') or '')=='中央';win=max(0,min(1,score*(1-(.13 if central else .08)*frag)));place=max(0,min(1,.28*score+.20*form+.20*pace+.18*suitability+.08*connections+.06*(1-frag)));show=max(0,min(1,.22*score+.22*form+.20*suitability+.16*pace+.08*connections+.07*pedigree+.05*(1-frag)))\n"
    "    return {'factors':factors,'weights':weights,'score':score,'win':win,'place':place,'show':show,'fragility':frag,'sparse':sparse,'evidence':ax('evidence',u(e.get('dataCompleteness'),.5))}\n"
    '\n'
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

    # One sole scorer per circuit. The embedded v207/v212/v3xx ranker is
    # retained as inert historical code until the surrounding legacy
    # diagnostics are extracted, but it must never run in live prediction:
    # its old coefficients are neither NAR nor JRA's current scoring method.
    from arvexq.prediction.final_marks import apply_core_marks

    def _rank_evaluations_core_marks(detail):
        return apply_core_marks(detail)

    _rank_evaluations_core_marks._arvexq_core_marks_wrapped = True
    _rank_evaluations_core_marks.__name__ = '_rank_evaluations'
    namespace['_rank_evaluations'] = _rank_evaluations_core_marks
