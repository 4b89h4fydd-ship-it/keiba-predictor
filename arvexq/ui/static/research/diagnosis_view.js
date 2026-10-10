/* Read-only all-runner display from recorded pre-off evidence. */
(function(root){
  'use strict';
  function render(r,p,deps){
    var original=deps.original(r),esc=deps.esc,by={};
    if(original&&Array.isArray(original.horses))original.horses.forEach(function(h){by[h.horseNumber]=h});
    var started=deps.started(r),rows=(p&&p.rows)||[],labels={pure:'純能力',trueRun:'代表走',sectional:'区間能力',positionScenario:'展開適性',conditions:'条件適性',opponentLevel:'相手水準',stateConsistency:'状態・安定性'};
    var body=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber}).map(function(h){
      var saved=by[h.horseNumber],row=rows.find(function(x){return x.horse&&x.horse.horseNumber===h.horseNumber})||{},
          ev=saved&&(saved.lockedEvaluation||saved),score=saved?ev.score:(!started?row.overallScoreExact:null),
          grade=saved?ev.grade:(!started?row.overallGrade:''),mark=saved?saved.mark:(!started?row.predMark:''),
          axes=saved&&saved.axes,notes=[];
      if(axes)Object.keys(labels).forEach(function(k){if(axes[k]!=null&&Number.isFinite(Number(axes[k])))notes.push(labels[k]+' '+Number(axes[k]).toFixed(3))});
      if(!saved&&!started&&row.overallReasons)notes=row.overallReasons.slice();
      return '<article class="horse-card diagnosis-merged-row"><div class="diagnosis-merged-head">'
        +'<button class="diagnosis-horse-main" data-horse-open="'+esc(h.horseNumber)+'"><span class="diagnosis-horse-name"><b>'+esc(h.horseNumber+' '+h.name)+'</b></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade">'+esc(grade||'未取得')+'</strong><b>'+esc(score!=null&&Number.isFinite(Number(score))?Number(score).toFixed(1):'未取得')+'</b>'
        +'<i class="diagnosis-ai-mark">'+esc(deps.scratch(h)?'取消':mark||'—')+'</i></span></div>'
        +'<p class="diag-explain">'+esc(notes.join(' / ')||(started?'発走前の診断根拠は未保存':'診断データ不足'))+'</p></article>';
    }).join('');
    return '<details class="card"><summary>全頭診断（'+esc((r.horses||[]).length)+'頭）</summary>'
      +'<p class="muted">'+esc(original?'発走前に保存された評価を表示しています。':(started?'発走前評価が未保存の馬は未取得と表示します。':'取得済み情報による暫定評価です。'))+'</p>'
      +'<div class="diagnosis-merged-list">'+body+'</div></details>';
  }
  root.ARVEXQDiagnosisView=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
