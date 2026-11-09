/* Read-only all-runner display from recorded pre-off evidence. */
(function(root){
  'use strict';

  function stage64Rows(r){
    var p=r&&r.prediction,st=p&&p.stages||{},ability=st.ability&&st.ability.value,
        circuit=r&&({'中央':'jra','地方':'nar'}[r.circuit]||r.circuit),
        probability=st.probability&&st.probability.value||{},styles=st.runningStyle&&st.runningStyle.value,
        marks=r&&r.predictionMarks;
    if(!r||r.predictionStatus!=='ready'||r.predictionModelVersion!=='arvexq-stage64-product-v1'||
       !p||p.predictionStatus!=='ready'||p.productionEligible!==true||
       p.modelVersion!==r.predictionModelVersion||p.raceId!==r.id||p.date!==r.date||
       p.circuit!==circuit||!ability||typeof ability!=='object'||
       !Array.isArray(r.horses)||!Array.isArray(marks)||marks.length!==5)return null;
    var known={},marked={},rows={},validMarks={'◎':1,'○':1,'▲':1,'△':1,'☆':1};
    r.horses.forEach(function(h){if(h&&Number.isInteger(Number(h.horseNumber))&&Number(h.horseNumber)>0)known[String(Number(h.horseNumber))]=true});
    for(var i=0;i<marks.length;i++){
      var m=marks[i],no=String(Number(m&&m.horseNumber)),mark=String(m&&m.mark||'');
      if(!known[no]||marked[no]||!validMarks[mark])return null;
      marked[no]=mark;
    }
    if(new Set(Object.values(marked)).size!==5)return null;
    r.horses.forEach(function(h){
      if(!h)return;
      var no=String(Number(h.horseNumber)),a=ability[no],w=probability.win&&probability.win[no],
          t=probability.top3&&probability.top3[no],s=styles&&styles[no];
      function unit(v){return v!=null&&Number.isFinite(Number(v))&&Number(v)>=0&&Number(v)<=1?Number(v):null}
      rows[no]={ability:unit(a),win:unit(w),top3:unit(t),style:Array.isArray(s)&&s.length===4&&
        s.every(function(v){return unit(v)!==null})?s.map(Number):null,mark:marked[no]||'',
        calibrated:!!(st.probability&&st.probability.calibrationVerified===true)};
    });
    return rows;
  }
  function storedRows(r){
    // The race's own frozen diagnosis, read from its stored
    // unifiedForecast — the same source ARVEXQProductionPrediction
    // builds its pre-off rows from, under the same acceptance gates
    // (identity, receipt hashes, trained-through, captured before
    // the off, roster reconciled by name, exactly one ◎). Returns a
    // {horseNumber: {score, grade, mark, reason}} map, or null when
    // the payload carries no verifiably pre-off diagnosis. The grade
    // is the stored grade, falling back to the final-win-probability
    // bands (S>=20% / A>=12% / B>=7% / C>=3.5% / D below) — never to
    // the ability score.
    var uf=r&&r.unifiedForecast;
    if(!uf||uf.version!=='arvexq-unified-live-v1'||uf.raceId!==r.id||
       uf.raceDate!==r.date||uf.circuit!==r.circuit||uf.researchOnly!==true||
       uf.probabilitiesCalibrated!==false||!Array.isArray(uf.roster)||
       !Array.isArray(uf.marks)||!Array.isArray(uf.diagnosis)||uf.roster.length<3||
       !Array.isArray(r.horses)||!/^[a-f0-9]{64}$/i.test(uf.receiptSha256||'')||
       !/^[a-f0-9]{64}$/i.test(uf.modelHash||'')||
       !(String(uf.trainedThrough||'')<String(r.date||''))||
       !(Date.parse(String(uf.capturedAt||''))<
         Date.parse(String(r.date)+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00')))
      return null;
    var roster={},horseByNo={},active=0,ok=true,
        inactive=function(h){return !!(h&&(h.scratched===true||h.withdrawn===true||
          /欠場|出走取消|取消|競走除外|除外/.test(String(h.status||''))))};
    uf.roster.forEach(function(x){
      var n=Number(x&&x.horseNumber);
      if(!Number.isInteger(n)||n<=0||roster[n])ok=false;
      roster[n]=String(x&&x.name||'');
    });
    r.horses.forEach(function(h){
      var n=Number(h&&h.horseNumber);
      if(!Number.isInteger(n)||n<=0||horseByNo[n]){ok=false;return}
      horseByNo[n]=h;
      if(!inactive(h))active++;
    });
    Object.keys(roster).forEach(function(k){
      var h=horseByNo[k];
      if(!h||roster[k]!==String(h.name||''))ok=false;
    });
    Object.keys(horseByNo).forEach(function(k){
      if(!inactive(horseByNo[k])&&!(k in roster))ok=false;
    });
    if(!ok||active<3)return null;
    var allow={'◎':1,'○':1,'▲':1,'△':1,'☆':1,'注':1},seen={},markMap={},best=0;
    uf.marks.forEach(function(x){
      var n=Number(x&&x.horseNumber),m=String(x&&x.markSymbol||'');
      if(!Number.isInteger(n)||!roster[n]||seen[n]||!allow[m])ok=false;
      seen[n]=true;markMap[n]=m;if(m==='◎')best++;
    });
    if(!ok||best!==1)return null;
    var out={};
    uf.diagnosis.forEach(function(d){
      var n=Number(d&&d.horseNumber);
      if(!Number.isInteger(n)||!roster[n]||out[n])return;
      var w=d.winProbability;
      out[n]={
        score:d.abilityScore!=null&&Number.isFinite(Number(d.abilityScore))?Math.round(Number(d.abilityScore)*1000)/10:null,
        grade:d.grade!=null&&String(d.grade)?String(d.grade):(w!=null&&Number.isFinite(Number(w))?(Number(w)>=0.2?'S':(Number(w)>=0.12?'A':(Number(w)>=0.07?'B':(Number(w)>=0.035?'C':'D')))):''),
        mark:markMap[n]||'',
        reason:d.reason?String(d.reason):''};
    });
    return out;
  }
  function gradeBand(grade){
    // Colour band for the S/A/B/C/D letter grades only. Any other
    // grade text (能力指数, 未取得, retired labels) stays unbanded so
    // colour never invents a strength the grade does not claim.
    var g=String(grade==null?'':grade).trim();
    return (g==='S'||g==='A'||g==='B'||g==='C'||g==='D')?' diagnosis-grade-'+g.toLowerCase():'';
  }
  function render(r,p,deps){
    var original=deps.original(r),stage=stage64Rows(r),esc=deps.esc,by={};
    if(original&&Array.isArray(original.horses))original.horses.forEach(function(h){by[h.horseNumber]=h});
    var started=deps.started(r),storedMap=started?storedRows(r):null,rows=(p&&p.rows)||[],labels={pure:'純能力',trueRun:'代表走',sectional:'区間能力',positionScenario:'展開適性',conditions:'条件適性',opponentLevel:'相手水準',stateConsistency:'状態・安定性'};
    var body=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber}).map(function(h){
      var saved=by[h.horseNumber],row=rows.find(function(x){return x.horse&&x.horse.horseNumber===h.horseNumber})||{},
          stageRow=!saved&&stage&&stage[String(h.horseNumber)],ev=saved&&(saved.lockedEvaluation||saved),
          // Stored diagnosis: when the race has started, the live
          // prediction rows are not proof of what was published
          // before the off, so the card falls back to the race's own
          // frozen unifiedForecast diagnosis (storedRows below, same
          // acceptance gates as ARVEXQProductionPrediction). Values
          // render exactly as published; a race whose payload fails
          // those gates keeps the honest blank.
          storedRow=started&&storedMap?storedMap[String(h.horseNumber)]:null,
          score=saved?ev.score:(stageRow?(stageRow.ability!==null?stageRow.ability*100:null):(!started?row.overallScoreExact:(storedRow?storedRow.score:null))),
          grade=saved?ev.grade:(stageRow?'能力指数':(!started?row.overallGrade:(storedRow?storedRow.grade:''))),
          mark=saved?saved.mark:(stageRow?stageRow.mark:(!started?row.predMark:(storedRow?storedRow.mark:''))),
          axes=saved&&saved.axes,notes=[];
      if(axes)Object.keys(labels).forEach(function(k){if(axes[k]!=null&&Number.isFinite(Number(axes[k])))notes.push(labels[k]+' '+Number(axes[k]).toFixed(3))});
      if(stageRow){
        if(stageRow.ability!==null)notes.push('能力指数 '+(stageRow.ability*100).toFixed(1)+'/100');
        if(stageRow.win!==null)notes.push('推定1着率 '+(stageRow.win*100).toFixed(1)+'%');
        if(stageRow.top3!==null)notes.push('推定3着内率 '+(stageRow.top3*100).toFixed(1)+'%');
        if(stageRow.style){
          var names=['前方','先行','中団','後方'],top=Math.max.apply(null,stageRow.style);
          notes.push('脚質傾向 '+names[stageRow.style.indexOf(top)]);
        }
        if(!stageRow.calibrated)notes.push('確率は未校正');
      }
      if(!saved&&!stageRow&&!started&&row.overallReasons)notes=row.overallReasons.slice();
      if(!saved&&!stageRow&&started&&storedRow&&storedRow.reason)notes=[storedRow.reason];
      var band=gradeBand(grade);
      return '<article class="horse-card diagnosis-merged-row'+band+'"><div class="diagnosis-merged-head diagnosis-view-head">'
        +'<button class="diagnosis-horse-main" data-horse-open="'+esc(h.horseNumber)+'"><span class="diagnosis-horse-name"><b>'+esc(h.horseNumber+' '+h.name)+'</b></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade'+band+'">'+esc(grade||'未取得')+'</strong><b>'+esc(score!=null&&Number.isFinite(Number(score))?Number(score).toFixed(1):'未取得')+'</b>'
        +'<i class="diagnosis-ai-mark">'+esc(deps.scratch(h)?'取消':mark||'—')+'</i></span></div>'
        +'<p class="diag-explain">'+esc(notes.join(' / ')||(started?'発走前の診断根拠は未保存':'診断データ不足'))+'</p></article>';
    }).join('');
    // No narration line under the summary (user decision 2026-11-04:
    // the 取得済み/保存済み explanatory note was clutter). The
    // per-horse diag-explain lines below are the content and stay.
    return '<details class="card" data-diagnosis-fold="1"'+(deps.open?' open':'')+'><summary>全頭診断（'+esc((r.horses||[]).length)+'頭）</summary>'
      +'<div class="diagnosis-merged-list">'+body+'</div></details>';
  }
  root.ARVEXQDiagnosisView=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
