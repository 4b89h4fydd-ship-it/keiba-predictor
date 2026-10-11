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
    'from arvexq.prediction.legacy.common import (\n'
    '    _v207_norm01,\n'
    '    _v207_component,\n'
    '    _v213_rank_percentiles,\n'
    '    _v213_zscore,\n'
    '    _v213_softmax,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.winner import (\n'
    '    _v207_winner_score,\n'
    '    _v212_role_feature_map,\n'
    '    _v212_p2_score,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.role_features import (\n'
    '    _saved_role_scores,\n'
    '    _v213_feature_rows,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.course import (\n'
    '    _v215_speed_ratio,\n'
    '    _v215_draw_score,\n'
    ')\n'
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
    'from arvexq.prediction.legacy.factors import (\n'
    '    _v313_horse_flow_adjust,\n'
    '    _v317_factor_weights,\n'
    '    _v317_factor_profile,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.professional import (\n'
    '    _v215_prof_feature_rows,\n'
    '    _v215_professional_p1,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    '# v218 tactical + conditional-role bridge.\n'
    '# v215/v213 remain the statistical bases. v218 strengthens the race-reading layer\n'
    '# using TRUE RUN, individual neighbour pressure, a probability mixture of pace shapes,\n'
    '# and role-specific compatibility. It does not use post-race information.\n'
    'from arvexq.prediction.legacy.tactical import V218_TACTICAL_MODEL_VERSION, V218_P1_BLEND\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.tactical import (\n'
    '    _v218_tactical_roles,\n'
    ')\n'
    '\n'
    '\n'
    'from arvexq.prediction.legacy.role_utilities import (\n'
    '    _v213_role_utilities,\n'
    ')\n'
    '\n'
    '\n'
    '\n'
    '\n'
    '\n'
    'def _rank_evaluations(detail):\n'
    "    horses=list(detail.get('horses') or [])\n"
    "    circuit=str(detail.get('circuit') or '')\n"
    '    use_v213=circuit in V213_VALIDATED_CIRCUITS\n'
    '    use_v207=circuit in V207_VALIDATED_CIRCUITS\n'
    '    v213=None\n'
    '    if use_v213 and horses:\n'
    '        try:v213=_v213_role_utilities(detail,horses)\n'
    '        except Exception:v213=None\n'
    '    p1prob=p2prob=p3prob=None\n'
    '    if v213:\n'
    '        u1,u2,u3,p1prob,p2prob,p3prob,core1,pro1,tactical1,p2_role,p3_role,tactical_audit=v213\n'
    '    for idx,horse in enumerate(horses):\n'
    "        e=horse.get('integratedEvaluation') or {}\n"
    '        legacy_p1,legacy_p2,legacy_p3=_saved_role_scores(horse)\n'
    '        v207_p1=_v207_winner_score(horse,legacy_p1) if use_v207 else legacy_p1\n'
    '        v212_p2=_v212_p2_score(horse) if use_v207 else legacy_p2\n'
    '        if v213:\n'
    '            active_p1=round(p1prob[idx]*100,4);active_p2=round(p2prob[idx]*100,4);active_p3=round(p3prob[idx]*100,4)\n'
    "            e['v213P1Utility']=round(core1[idx],8);e['v215ProfessionalP1Utility']=round(pro1[idx],8)\n"
    "            e['v215P1Utility']=round((1.0-V215_P1_BLEND)*core1[idx]+V215_P1_BLEND*pro1[idx],8)\n"
    "            e['v218TacticalUtility']=round(tactical1[idx],8);e['v218P1Utility']=round(u1[idx],8);e['v218P2RoleFit']=round(p2_role[idx],8);e['v218P3RoleFit']=round(p3_role[idx],8);e['v218Audit']=tactical_audit[idx];e['v217Audit']=tactical_audit[idx]\n"
    "            e['v213P2Utility']=round(u2[idx],8);e['v213P3Utility']=round(u3[idx],8)\n"
    "            e['v213P1Probability']=active_p1;e['v218P1Probability']=active_p1;e['v213P2Probability']=active_p2;e['v213P3Probability']=active_p3\n"
    '        else:\n'
    '            active_p1=v207_p1 if use_v207 else legacy_p1;active_p2=v212_p2 if use_v207 else legacy_p2;active_p3=legacy_p3\n'
    "        e['legacyP1Score']=legacy_p1;e['legacyP2Score']=legacy_p2;e['legacyP3Score']=legacy_p3\n"
    "        e['v207WinnerScore']=v207_p1 if use_v207 else None;e['v212P2Score']=v212_p2 if use_v207 else None\n"
    "        e['p1Score']=active_p1;e['p2Score']=active_p2;e['p3Score']=active_p3\n"
    "        e['roleModelVersion']=V218_TACTICAL_MODEL_VERSION if v213 else PREDICTION_ENGINE_VERSION\n"
    "        e['winnerModelVersion']=V218_TACTICAL_MODEL_VERSION if v213 else (V207_WINNER_MODEL_VERSION if use_v207 else ('central-winner-v317-consensus-rebuild' if str(detail.get('circuit') or '')=='中央' else 'local-winner-v317-consensus-rebuild'))\n"
    "        e['p2ModelVersion']=V213_ROLE_MODEL_VERSION if v213 else (V212_P2_MODEL_VERSION if use_v207 else 'legacy-p2-central-unvalidated')\n"
    "        e['p3ModelVersion']=V213_ROLE_MODEL_VERSION if v213 else 'legacy-p3'\n"
    "        e['winnerModelValidated']=bool(v213 or use_v207);e['p2ModelValidated']=bool(v213 or use_v207);e['p3ModelValidated']=bool(v213)\n"
    '\n'
    "    legacy_sorted=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('legacyP1Score') or 0),-float((h.get('integratedEvaluation') or {}).get('score') or 0),int(h.get('horseNumber') or 0)))\n"
    "    for i,h in enumerate(legacy_sorted):(h.get('integratedEvaluation') or {}).__setitem__('legacyP1Rank',i+1)\n"
    "    v207_sorted=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('v207WinnerScore') or 0),int(h.get('horseNumber') or 0)))\n"
    '\n'
    '    # v300: rank P1/P2/P3 first, then select ◎ with a winner-only market-independent\n'
    '    # consensus. P2/P3 NEVER enter the winner selector; they remain role models.\n'
    "    p1_sorted=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('p1Score') or 0),-float((h.get('integratedEvaluation') or {}).get('score') or 0),int(h.get('horseNumber') or 0)))\n"
    "    p2_sorted=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('p2Score') or 0),int(h.get('horseNumber') or 0)))\n"
    "    p3_sorted=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('p3Score') or 0),int(h.get('horseNumber') or 0)))\n"
    "    for i,h in enumerate(p1_sorted):(h.get('integratedEvaluation') or {}).__setitem__('p1Rank',i+1)\n"
    "    for i,h in enumerate(p2_sorted):(h.get('integratedEvaluation') or {}).__setitem__('p2Rank',i+1)\n"
    "    for i,h in enumerate(p3_sorted):(h.get('integratedEvaluation') or {}).__setitem__('p3Rank',i+1)\n"
    '\n'
    '    def _axis(h,key,default=.5):\n'
    "        e=h.get('integratedEvaluation') or {};a=e.get('v218Audit') or e.get('v217Audit') or {}\n"
    '        try:return max(0.0,min(1.0,float(a.get(key) if a.get(key) is not None else default)))\n'
    '        except Exception:return default\n'
    '    def _frag(h):\n'
    "        e=h.get('integratedEvaluation') or {};a=e.get('v218Audit') or e.get('v217Audit') or {};pp=a.get('positionPressure') or {}\n"
    "        try:return max(0.0,min(1.0,float(pp.get('local') or 0)))\n"
    '        except Exception:return 0.0\n'
    "    circuit=str(detail.get('circuit') or '')\n"
    "    method=_v312_method(circuit);central_race=circuit=='中央';day_profile=_v313_same_day_mark_profile(detail);day_adjust=[_v313_horse_flow_adjust(h,day_profile,len(horses)) for h in horses]\n"
    '    factor_profiles=[_v317_factor_profile(detail,h) for h in horses]\n'
    '    for i,h in enumerate(horses):\n'
    "        e=h.get('integratedEvaluation') or {};e['researchFactors']={k:round(v,8) for k,v in factor_profiles[i]['factors'].items()};e['researchFactorWeights']={k:round(v,8) for k,v in factor_profiles[i]['weights'].items()};e['researchConsensusScore']=round(factor_profiles[i]['score'],8);e['researchSparse']=bool(factor_profiles[i]['sparse']);e['researchModel']='v317-expert-ai-consensus'\n"
    "    detail['sameDayMarkProfile']=day_profile\n"
    '    def _duel_prob(a,b):\n'
    "        ia=horses.index(a);ib=horses.index(b);fa=factor_profiles[ia]['factors'];fb=factor_profiles[ib]['factors'];ea=a.get('integratedEvaluation') or {};eb=b.get('integratedEvaluation') or {}\n"
    "        pa=max(0.0,float(ea.get('p1Score') or 0));pb=max(0.0,float(eb.get('p1Score') or 0));scale=max(1.0,pa+pb);pa/=scale;pb/=scale\n"
    "        raw=.08*(pa-pb)+.22*(fa['ability']-fb['ability'])+.11*(fa['classLevel']-fb['classLevel'])+.13*(fa['form']-fb['form'])+.18*(fa['pace']-fb['pace'])+.16*(fa['suitability']-fb['suitability'])+.06*(fa['connections']-fb['connections'])+.06*(fa['pedigree']-fb['pedigree'])\n"
    "        raw+=(.07 if central_race else .04)*(factor_profiles[ib]['fragility']-factor_profiles[ia]['fragility']);raw*=.50+.50*min(_axis(a,'evidence',.5),_axis(b,'evidence',.5))\n"
    '        try:return 1.0/(1.0+math.exp(-8.0*raw))\n'
    '        except Exception:return .5\n'
    '    duel_rates=[]\n'
    '    for a in horses:\n'
    '        ps=[_duel_prob(a,b) for b in horses if b is not a];duel_rates.append(sum(ps)/len(ps) if ps else .5)\n'
    '    if horses:\n'
    '        mx=max(duel_rates);dex=[math.exp((x-mx)/.085) for x in duel_rates];ds=sum(dex) or 1.0;duel_prob=[x/ds for x in dex]\n'
    '    else:duel_prob=[]\n'
    '\n'
    '    # v317 expert/AI consensus factor prior. Market odds/popularity remain excluded.\n'
    '    win_raw=[]\n'
    '    for i,h in enumerate(horses):\n'
    "        if central_race:legacy=.18*_axis(h,'pure')+.22*_axis(h,'trueRun')+.17*_axis(h,'sectional')+.17*_axis(h,'positionScenario')+.09*_axis(h,'conditions')+.10*_axis(h,'opponentLevel')+.04*_axis(h,'stateConsistency')+.03*_axis(h,'flexibility',.5)\n"
    "        else:legacy=.27*_axis(h,'pure')+.22*_axis(h,'trueRun')+.13*_axis(h,'sectional')+.14*_axis(h,'positionScenario')+.09*_axis(h,'conditions')+.06*_axis(h,'opponentLevel')+.04*_axis(h,'stateConsistency')+.05*_axis(h,'evidence',.5)\n"
    "        q=.72*factor_profiles[i]['win']+.28*legacy+day_adjust[i]*.035\n"
    "        win_raw.append(max(.001,q*(1-float(method.get('fragPenalty') or .08)*_frag(h))))\n"
    '    if win_raw:\n'
    '        mx=max(win_raw);temp=.095 if central_race else .105;wex=[math.exp((x-mx)/temp) for x in win_raw];ws=sum(wex) or 1.0;win_prob=[x/ws for x in wex]\n'
    '    else:win_prob=[]\n'
    "    p1_vals=[max(0.0,float((h.get('integratedEvaluation') or {}).get('p1Score') or 0)) for h in horses];p1_sum=sum(p1_vals) or 1.0;p1_prob=[x/p1_sum for x in p1_vals]\n"
    "    learn=detail.get('winnerLearningProfile') if isinstance(detail.get('winnerLearningProfile'),dict) else {};base_lw=_v312_base_winner_weights(str(detail.get('circuit') or ''));lw=learn.get('weights') if isinstance(learn.get('weights'),dict) else base_lw\n"
    "    wp1=float(lw.get('p1',.58));wwe=float(lw.get('winEvidence',.24));wpa=float(lw.get('pairwise',.18));consensus=[max(1e-12,wp1*p1_prob[i]+wwe*win_prob[i]+wpa*duel_prob[i]) for i in range(len(horses))]\n"
    "    power=max(.55,min(1.65,float(learn.get('power') or 1.0))) if learn.get('active') else 1.0;consensus=[x**power for x in consensus];cs=sum(consensus) or 1.0;consensus=[x/cs for x in consensus]\n"
    "    shrink=max(0.0,min(.25,float(learn.get('shrink') or 0.0))) if learn.get('active') else 0.0\n"
    "    factor_ev=sum(float(x.get('evidence') or .5) for x in factor_profiles)/max(1,len(factor_profiles));shrink=max(shrink,max(0.0,min(.12,(.68-factor_ev)*.22)))\n"
    '    if shrink and horses:\n'
    '        uni=1.0/len(horses);consensus=[(1-shrink)*x+shrink*uni for x in consensus];cs=sum(consensus) or 1.0;consensus=[x/cs for x in consensus]\n'
    '    for i,h in enumerate(horses):\n'
    "        e=h.get('integratedEvaluation') or {};e['pairwiseWinRate']=round(duel_rates[i],8);e['pairwiseProbability']=round(duel_prob[i],8);e['winEvidenceProbability']=round(win_prob[i],8);e['winnerConsensusProbability']=round(consensus[i],8);e['winnerLearningProfileId']=str(learn.get('profileId') or 'baseline');e['winnerLearningActive']=bool(learn.get('active'));e['researchConfidenceShrink']=round(shrink,8);e['sameDayMarkAdjustment']=round(day_adjust[i],8);e['sameDayFlowLabel']=str(day_profile.get('flowLabel') or '中立')\n"
    "    for rank,h in enumerate(sorted(horses,key=lambda z:(-float((z.get('integratedEvaluation') or {}).get('pairwiseWinRate') or .5),-float((z.get('integratedEvaluation') or {}).get('p1Score') or 0),int(z.get('horseNumber') or 0))),1):(h.get('integratedEvaluation') or {})['pairwiseRank']=rank\n"
    "    for rank,h in enumerate(sorted(horses,key=lambda z:(-float((z.get('integratedEvaluation') or {}).get('winEvidenceProbability') or 0),int(z.get('horseNumber') or 0))),1):(h.get('integratedEvaluation') or {})['winEvidenceRank']=rank\n"
    "    cons_sorted=sorted(horses,key=lambda z:(-float((z.get('integratedEvaluation') or {}).get('winnerConsensusProbability') or 0),-float((z.get('integratedEvaluation') or {}).get('p1Score') or 0),int(z.get('horseNumber') or 0)))\n"
    "    for rank,h in enumerate(cons_sorted,1):(h.get('integratedEvaluation') or {})['winnerConsensusRank']=rank\n"
    '\n'
    '    winner_leader=p1_sorted[0] if p1_sorted else None\n'
    '    if winner_leader and cons_sorted and cons_sorted[0] is not winner_leader and len(p1_sorted)>1:\n'
    "        best=cons_sorted[0];te=winner_leader.get('integratedEvaluation') or {};be=best.get('integratedEvaluation') or {}\n"
    '        itop=horses.index(winner_leader);ibest=horses.index(best);gap=(p1_prob[itop] if itop<len(p1_prob) else 0)-(p1_prob[ibest] if ibest<len(p1_prob) else 0)\n'
    "        tc=float(te.get('winnerConsensusProbability') or 0);bc=float(be.get('winnerConsensusProbability') or 0);tp=float(te.get('pairwiseProbability') or 0);bp=float(be.get('pairwiseProbability') or 0);tw=float(te.get('winEvidenceProbability') or 0);bw=float(be.get('winEvidenceProbability') or 0);bev=_axis(best,'evidence',.5)\n"
    '        if central_race:\n'
    '            if gap<=.045 and bev>=.30 and bc>=tc*1.015 and bp>=tp*.995 and bw>=tw*.995:winner_leader=best\n'
    '            elif gap<=.070 and _frag(p1_sorted[0])>=.55 and bev>=.34 and bc>=tc*1.06 and bp>=tp*1.01 and bw>=tw*1.02:winner_leader=best\n'
    '        else:\n'
    '            if gap<=.025 and bev>=.26 and bc>=tc*.995 and bp>=tp*.985:winner_leader=best\n'
    '            elif gap<=.045 and bev>=.30 and bc>=tc*1.04 and bp>=tp*1.01 and bw>=tw*1.02:winner_leader=best\n'
    '            elif gap<=.060 and _frag(p1_sorted[0])>=.58 and bc>=tc*1.075 and bp>=tp*1.035 and bw>=tw*1.04:winner_leader=best\n'
    '    if winner_leader:\n'
    "        we=winner_leader.get('integratedEvaluation') or {};runner=next((h for h in cons_sorted if h is not winner_leader),None);re=(runner.get('integratedEvaluation') or {}) if runner else {};margin=float(we.get('winnerConsensusProbability') or 0)-float(re.get('winnerConsensusProbability') or 0);ev=_axis(winner_leader,'evidence',.5);raw_agree=winner_leader is (p1_sorted[0] if p1_sorted else None);conf=max(0.0,min(1.0,.27+margin*max(5.5,len(horses)*.60)+(.13 if raw_agree else .075)+ev*.21-_frag(winner_leader)*.16));stable_floor=float(method.get('stableFloor') or (.64 if central_race else .56));margin_floor=(1/max(1,len(horses)))*(.075 if central_race else .050);we['winnerDecisionStable']=bool(conf>=stable_floor and (raw_agree or margin>=max(.006,margin_floor)));we['axisConfidence']=round(conf,8);we['winDecisionOverride']=bool(not raw_agree)\n"
    '\n'
    '    # v312 podium-recall marks: winner / second / third roles are scored separately,\n'
    '    # then merged into a compact 5-7 horse set.  The pre-race lock uses these marks,\n'
    '    # so the daily 3-horse-complete KPI is measured against the exact frozen prediction.\n'
    '    seven=[];robust=[]\n'
    '    for h in horses:\n'
    "        e=h.get('integratedEvaluation') or {};sv=_axis(h,'sevenAxisScore',max(0.0,min(1.0,float(e.get('score') or 50)/100)));ev=_axis(h,'evidence',.5);pr=_frag(h)\n"
    "        seven.append(sv);robust.append(max(.001,.48*sv+.20*max(0.0,min(1.0,float(e.get('score') or 50)/100))+.17*ev+.15*(1-pr)))\n"
    '    s7=sum(seven) or 1.0;sr=sum(robust) or 1.0;axis_raw=[]\n'
    "    p2_vals=[max(0.0,float((h.get('integratedEvaluation') or {}).get('p2Score') or 0)) for h in horses]\n"
    "    p3_vals=[max(0.0,float((h.get('integratedEvaluation') or {}).get('p3Score') or 0)) for h in horses]\n"
    '    p2_dist=_prob_vector(p2_vals);p3_dist=_prob_vector(p3_vals);uniform=1.0/max(1,len(horses))\n'
    '    def _recent_top3(h):\n'
    "        runs=(h.get('recentRaces') or h.get('allPastRuns') or [])[:5];good=tot=0\n"
    '        for rr in runs:\n'
    '            if not isinstance(rr,dict):continue\n'
    "            try:f=int(rr.get('finish') or rr.get('finishPosition') or rr.get('rank') or 0)\n"
    '            except Exception:f=0\n'
    '            if f>0:tot+=1;good+=1 if f<=3 else 0\n'
    '        return good/tot if tot else .25\n'
    '    def _comp(h,names,default=.5):\n'
    "        e=h.get('integratedEvaluation') or {};c=e.get('components') if isinstance(e.get('components'),dict) else {}\n"
    '        for key in names:\n'
    '            if c.get(key) is None:continue\n'
    '            try:\n'
    '                x=float(c.get(key));return max(0.0,min(1.0,x/100.0 if x>1.5 else x))\n'
    '            except Exception:pass\n'
    '        return default\n'
    '    second_scores=[];third_scores=[];podium_scores=[]\n'
    '    for i,h in enumerate(horses):\n'
    "        e=h.get('integratedEvaluation') or {};p1=p1_prob[i] if i<len(p1_prob) else uniform;p2=p2_dist[i] if i<len(p2_dist) else uniform;p3=p3_dist[i] if i<len(p3_dist) else uniform\n"
    "        tr=_axis(h,'trueRun',.5);sec=_axis(h,'sectional',.5);scn=_axis(h,'positionScenario',.5);cond=_axis(h,'conditions',.5);opp=_axis(h,'opponentLevel',.5);state=_axis(h,'stateConsistency',.5);ev=_axis(h,'evidence',.5);frag=_frag(h);recent=_recent_top3(h);course=_comp(h,['courseFit','trackFit'],.5)\n"
    '        if central_race:\n'
    "            s2=.28*p2+.12*p1+.30*factor_profiles[i]['place']+.08*tr+.06*sec+.06*scn+.04*opp+.03*robust[i]+.03*recent;s2*=1-.07*frag\n"
    "            s3=.27*p3+.34*factor_profiles[i]['show']+.09*sec+.08*tr+.06*scn+.06*robust[i]+.05*recent+.025*opp+.025*cond+.02*ev;s3*=1-.045*frag\n"
    '        else:\n'
    "            s2=.30*p2+.10*p1+.30*factor_profiles[i]['place']+.08*state+.07*course+.06*scn+.03*cond+.03*recent+.03*robust[i];s2*=1-.035*frag\n"
    "            s3=.29*p3+.34*factor_profiles[i]['show']+.09*state+.08*course+.07*scn+.05*recent+.03*cond+.03*robust[i]+.02*ev;s3*=1-.025*frag\n"
    "        core_scale=1.0 if int(day_profile.get('markRaces') or 0)>=3 else .55;s2+=day_adjust[i]*.38*core_scale;s3+=day_adjust[i]*.65*core_scale\n"
    '        s2=max(0.0,min(1.0,s2));s3=max(0.0,min(1.0,s3));pod=max(0.0,min(1.0,max(.86*p1+day_adjust[i]*.12,s2,s3)*.72+robust[i]*.18+ev*.10+day_adjust[i]*.10))\n'
    '        second_scores.append(s2);third_scores.append(s3);podium_scores.append(pod)\n'
    "        axis=max(.0001,.30*p1+.16*p2+.12*p3+.24*factor_profiles[i]['score']+.10*factor_profiles[i]['place']+.08*(robust[i]/sr));e['axisProbabilityRaw']=round(axis,8);e['p2RecallScore']=round(s2,8);e['p3RecallScore']=round(s3,8);e['podiumRecallScore']=round(pod,8);axis_raw.append(axis)\n"
    '    axis_total=sum(axis_raw) or 1.0\n'
    "    general=sorted(horses,key=lambda h:(-float((h.get('integratedEvaluation') or {}).get('axisProbabilityRaw') or 0),-float((h.get('integratedEvaluation') or {}).get('p1Score') or 0),int(h.get('horseNumber') or 0)))\n"
    "    p2_recall=sorted(range(len(horses)),key=lambda i:(-second_scores[i],int(horses[i].get('horseNumber') or 0)))\n"
    "    p3_recall=sorted(range(len(horses)),key=lambda i:(-third_scores[i],int(horses[i].get('horseNumber') or 0)))\n"
    "    podium_recall=sorted(range(len(horses)),key=lambda i:(-podium_scores[i],-axis_raw[i],int(horses[i].get('horseNumber') or 0)))\n"
    '    p2_rank={idx:rank+1 for rank,idx in enumerate(p2_recall)};p3_rank={idx:rank+1 for rank,idx in enumerate(p3_recall)};pod_rank={idx:rank+1 for rank,idx in enumerate(podium_recall)}\n'
    '    # v316 independent-route diversity ranks; market fields are not used.\n'
    '    def _ranks(vals):\n'
    "        order=sorted(range(len(vals)),key=lambda i:(-float(vals[i]),int(horses[i].get('horseNumber') or 0)))\n"
    '        return {idx:rank+1 for rank,idx in enumerate(order)}\n'
    "    dim_vals=[[factor_profiles[i]['factors'][k] for i in range(len(horses))] for k in ('ability','form','pace','suitability','connections')]\n"
    '    dim_ranks=[_ranks(v) for v in dim_vals]\n'
    '    diversity=[]\n'
    '    for i,h in enumerate(horses):\n'
    '        rs=[m.get(i,99) for m in dim_ranks];hits=sum(1 for x in rs if x<=4);best=min(rs) if rs else 99\n'
    '        score=max(0.0,min(1.0,.52*podium_scores[i]+.18*third_scores[i]+.10*second_scores[i]+.10*robust[i]+.08*(hits/5)+(.04 if best<=2 else 0)))\n'
    "        diversity.append((score,hits,best));e=h.get('integratedEvaluation') or {};e['recallDiversityScore']=round(score,8);e['recallDiversityHits']=hits;e['recallDiversityBest']=best\n"
    '    for i,h in enumerate(horses):\n'
    "        e=h.get('integratedEvaluation') or {};e['axisProbability']=round(axis_raw[i]/axis_total,8);e['axisRank']=general.index(h)+1;e['p2RecallRank']=p2_rank[i];e['p3RecallRank']=p3_rank[i];e['podiumRecallRank']=pod_rank[i];e['mark']=''\n"
    '    selected=[]\n'
    '    def _take(h,mark):\n'
    '        if not h or h in selected:return False\n'
    "        (h.get('integratedEvaluation') or {})['mark']=mark;selected.append(h);return True\n"
    "    _take(winner_leader or (general[0] if general else None),'◎')\n"
    "    second_pick=next((horses[i] for i in p2_recall if horses[i] not in selected),None);_take(second_pick,'○')\n"
    '    third_core=next((horses[i] for i in podium_recall if horses[i] not in selected and (p2_rank[i]<=5 or p3_rank[i]<=5 or (general.index(horses[i])+1)<=4)),None)\n'
    '    if third_core is None:third_core=next((horses[i] for i in podium_recall if horses[i] not in selected),None)\n'
    "    _take(third_core,'▲')\n"
    '    plus_pool=[]\n'
    '    for i,h in enumerate(horses):\n'
    '        if h in selected:continue\n'
    '        p1=p1_prob[i] if i<len(p1_prob) else uniform\n'
    "        if p1>=uniform*.72 and podium_scores[i]>=.48 and (_axis(h,'trueRun',.5)>=.46 or _axis(h,'positionScenario',.5)>=.50 or p2_rank[i]<=4):plus_pool.append((.34*p1+.34*podium_scores[i]+.16*second_scores[i]+.16*third_scores[i],h))\n"
    "    plus_pool.sort(key=lambda z:(-z[0],int(z[1].get('horseNumber') or 0)))\n"
    "    if plus_pool:_take(plus_pool[0][1],'☆+')\n"
    '    show_pick=next((horses[i] for i in p3_recall if horses[i] not in selected and (p3_rank[i]<=6 or p3_dist[i]>=uniform*.72)),None)\n'
    '    if show_pick is None:show_pick=next((horses[i] for i in p3_recall if horses[i] not in selected),None)\n'
    "    _take(show_pick,'☆')\n"
    '    rescue_pool=[]\n'
    '    for i in p3_recall:\n'
    '        h=horses[i]\n'
    '        if h in selected:continue\n'
    "        e=h.get('integratedEvaluation') or {};hist=len(h.get('recentRaces') or h.get('allPastRuns') or [])\n"
    "        if (p3_rank[i]<=6 or p3_dist[i]>=uniform*.76) and (_axis(h,'evidence',.5)>=.25 or hist>=2):\n"
    "            rs=.58*third_scores[i]+.18*podium_scores[i]+.12*_axis(h,'trueRun',.5)+.12*_axis(h,'positionScenario',.5)\n"
    '            rescue_pool.append((rs,h))\n'
    "    rescue_pool.sort(key=lambda z:(-z[0],int(z[1].get('horseNumber') or 0)))\n"
    "    winner_stable=bool((winner_leader.get('integratedEvaluation') or {}).get('winnerDecisionStable')) if winner_leader else False\n"
    "    hard_recall=(not winner_stable) or float(day_profile.get('deficit') or 0)>=.22\n"
    "    if rescue_pool and rescue_pool[0][0]>=(.47 if central_race else .48):_take(rescue_pool[0][1],'△')\n"
    '    elif len(horses)>=10 and hard_recall:\n'
    "        soft=next((horses[i] for i in p3_recall if horses[i] not in selected and p3_rank[i]<=7 and _axis(horses[i],'evidence',.5)>=.20),None)\n"
    "        if soft is not None:_take(soft,'△')\n"
    '    target=min(len(horses),7 if len(horses)>=12 else (7 if len(horses)>=10 and hard_recall else (6 if len(horses)>=7 else min(len(horses),5))))\n'
    '    # Reserve one lower mark for a horse supported by multiple independent routes.\n'
    '    div_pool=[]\n'
    '    for i,h in enumerate(horses):\n'
    '        if h in selected:continue\n'
    "        score,hits,best=diversity[i];ev=_axis(h,'evidence',.5)\n"
    '        if ev>=.22 and (hits>=2 or best<=2) and podium_scores[i]>=.36:div_pool.append((score,h,i))\n'
    "    div_pool.sort(key=lambda z:(-z[0],int(z[1].get('horseNumber') or 0)))\n"
    "    if len(selected)<target and div_pool:_take(div_pool[0][1],'注+')\n"
    '    cov=[]\n'
    '    for i,h in enumerate(horses):\n'
    '        if h in selected:continue\n'
    "        role_rank=min(p2_rank[i],p3_rank[i],general.index(h)+1);score=.56*podium_scores[i]+.17*second_scores[i]+.20*third_scores[i]+.07*_axis(h,'evidence',.5)+(.05 if role_rank<=5 else 0)\n"
    '        if podium_scores[i]>=.43 or p2_rank[i]<=5 or p3_rank[i]<=6 or (general.index(h)+1)<=6:cov.append((score,h,i))\n'
    "    cov.sort(key=lambda z:(-z[0],int(z[1].get('horseNumber') or 0)));labels=['注'] if any(str((h.get('integratedEvaluation') or {}).get('mark') or '')=='注+' for h in selected) else ['注+','注']\n"
    '    for score,h,i in cov:\n'
    '        if len(selected)>=target or not labels:break\n'
    "        strong=podium_scores[i]>=.56 and (p2_rank[i]<=4 or p3_rank[i]<=4 or _axis(h,'positionScenario',.5)>=.58)\n"
    "        mark='注+' if strong and '注+' in labels else ('注' if '注' in labels else labels[0]);labels.remove(mark);_take(h,mark)\n"
    '    # v316 final shadow swap: only 注/注+ can be replaced, never core marks.\n'
    "    unmarked=[(diversity[i][0],h,i) for i,h in enumerate(horses) if h not in selected and diversity[i][1]>=2 and _axis(h,'evidence',.5)>=.24]\n"
    "    weak=[(diversity[horses.index(h)][0],h) for h in selected if str((h.get('integratedEvaluation') or {}).get('mark') or '') in {'注','注+'}]\n"
    '    if unmarked and weak:\n'
    "        unmarked.sort(key=lambda z:(-z[0],int(z[1].get('horseNumber') or 0)));weak.sort(key=lambda z:(z[0],int(z[1].get('horseNumber') or 0)))\n"
    '        if unmarked[0][0]>=weak[0][0]+.055:\n'
    "            sh=unmarked[0][1];wk=weak[0][1];mk=str((wk.get('integratedEvaluation') or {}).get('mark') or '注');(wk.get('integratedEvaluation') or {})['mark']='';selected.remove(wk);_take(sh,mk)\n"
    "    evidence_count=sum(1 for h in horses if not (h.get('integratedEvaluation') or {}).get('neutralPrior') and (int((h.get('integratedEvaluation') or {}).get('samples') or 0)>0 or bool((h.get('integratedEvaluation') or {}).get('components'))));mark_confident=evidence_count>=max(2,(len(horses)+2)//3)\n"
    "    mark_order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注+':7,'注':8}\n"
    "    ranked_marks=sorted(horses,key=lambda h:(mark_order.get(str((h.get('integratedEvaluation') or {}).get('mark') or ''),99),-float((h.get('integratedEvaluation') or {}).get('podiumRecallScore') or 0),int(h.get('horseNumber') or 0)))\n"
    '    for i,horse in enumerate(ranked_marks):\n'
    "        e=horse.get('integratedEvaluation') or {};score=float(e.get('score') or 0);e.update({'rank':i+1,'markConfidence':'通常' if mark_confident else '暫定','markProvisional':bool(not mark_confident),'grade':'S' if score>=80 else 'A' if score>=70 else 'B' if score>=55 else 'C'})\n"
    "    active_top=int(winner_leader.get('horseNumber') or 0) if winner_leader else 0;legacy_top=int(legacy_sorted[0].get('horseNumber') or 0) if legacy_sorted else 0;v207_top=int(v207_sorted[0].get('horseNumber') or 0) if v207_sorted else 0\n"
    "    detail['researchConsensusV317']={'pillars':['ability','classLevel','form','pace','suitability','connections','pedigree','relative'],'marketBlind':True,'circuit':circuit,'temporalValidationRequired':True}\n"
    "    detail['modelComparison']={'activeVersion':V218_TACTICAL_MODEL_VERSION if v213 else (V207_WINNER_MODEL_VERSION if use_v207 else ('central-winner-v317-consensus-rebuild' if central_race else 'local-winner-v317-consensus-rebuild')),'legacyVersion':V207_WINNER_MODEL_VERSION if v213 else 'arvexq-edge-2026.09-v14-winner-role-split','validatedCircuit':bool(v213 or use_v207),'activeTop1':active_top,'legacyTop1':v207_top if v213 else legacy_top,'top1Agreement':bool(active_top and active_top==(v207_top if v213 else legacy_top)),'circuitMethod':method.get('id'),'backtest':dict(V213_BACKTEST_AUDIT) if v213 else (dict(V207_BACKTEST_AUDIT) if use_v207 else {'note':'中央は地方499Rモデルを転用せず、v317専門家/AI共通因子＋相対比較モデルを使用。未使用Holdoutでの昇格検証は継続'})}\n"
    '    return detail\n'
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

    # Final marks must follow the current ability/record engine. The legacy ranker is
    # retained only for auxiliary diagnostics and lower-mark context.
    from arvexq.prediction.final_marks import apply_core_marks

    legacy_rank = namespace.get('_rank_evaluations')
    if callable(legacy_rank) and not getattr(legacy_rank, '_arvexq_core_marks_wrapped', False):
        def _rank_evaluations_core_marks(detail):
            result = legacy_rank(detail)
            target = result if isinstance(result, dict) else detail
            return apply_core_marks(target)

        _rank_evaluations_core_marks._arvexq_core_marks_wrapped = True
        _rank_evaluations_core_marks.__name__ = '_rank_evaluations'
        namespace['_rank_evaluations'] = _rank_evaluations_core_marks
