/* Read-only all-runner display from recorded pre-off evidence. */
(function(root){
  'use strict';

  function stage64Rows(r){
    var p=r&&r.prediction,st=p&&p.stages||{},ability=st.ability&&st.ability.value,
        probability=st.probability&&st.probability.value||{},styles=st.runningStyle&&st.runningStyle.value,
        marks=r&&r.predictionMarks;
    if(!r||r.predictionStatus!=='ready'||r.predictionModelVersion!=='arvexq-stage64-product-v1'||
       !p||p.predictionStatus!=='ready'||p.productionEligible!==true||
       p.modelVersion!==r.predictionModelVersion||p.raceId!==r.id||p.date!==r.date||
       p.circuit!==r.circuit||!ability||typeof ability!=='object'||
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
  function render(r,p,deps){
    var original=deps.original(r),stage=stage64Rows(r),esc=deps.esc,by={};
    if(original&&Array.isArray(original.horses))original.horses.forEach(function(h){by[h.horseNumber]=h});
    var started=deps.started(r),rows=(p&&p.rows)||[],labels={pure:'純能力',trueRun:'代表走',sectional:'区間能力',positionScenario:'展開適性',conditions:'条件適性',opponentLevel:'相手水準',stateConsistency:'状態・安定性'};
    var body=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber}).map(function(h){
      var saved=by[h.horseNumber],row=rows.find(function(x){return x.horse&&x.horse.horseNumber===h.horseNumber})||{},
          stageRow=!saved&&stage&&stage[String(h.horseNumber)],ev=saved&&(saved.lockedEvaluation||saved),
          score=saved?ev.score:(stageRow?(stageRow.ability!==null?stageRow.ability*100:null):(!started?row.overallScoreExact:null)),
          grade=saved?ev.grade:(stageRow?'能力指数':(!started?row.overallGrade:'')),
          mark=saved?saved.mark:(stageRow?stageRow.mark:(!started?row.predMark:'')),
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
      return '<article class="horse-card diagnosis-merged-row"><div class="diagnosis-merged-head">'
        +'<button class="diagnosis-horse-main" data-horse-open="'+esc(h.horseNumber)+'"><span class="diagnosis-horse-name"><b>'+esc(h.horseNumber+' '+h.name)+'</b></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade">'+esc(grade||'未取得')+'</strong><b>'+esc(score!=null&&Number.isFinite(Number(score))?Number(score).toFixed(1):'未取得')+'</b>'
        +'<i class="diagnosis-ai-mark">'+esc(deps.scratch(h)?'取消':mark||'—')+'</i></span></div>'
        +'<p class="diag-explain">'+esc(notes.join(' / ')||(started?'発走前の診断根拠は未保存':'診断データ不足'))+'</p></article>';
    }).join('');
    return '<details class="card"><summary>全頭診断（'+esc((r.horses||[]).length)+'頭）</summary>'
      +'<p class="muted">'+esc(original?'発走前に保存された評価を表示しています。':(stage?'公開Stage64の能力・確率・印を表示。発走前の固定原本の確認とは別です。':(started?'発走前評価が未保存の馬は未取得と表示します。':'取得済み情報による暫定評価です。')))+'</p>'
      +'<div class="diagnosis-merged-list">'+body+'</div></details>';
  }
  root.ARVEXQDiagnosisView=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
