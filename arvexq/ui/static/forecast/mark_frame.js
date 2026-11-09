/* Read-only symbol display of authorized server prediction; no ranking here. */
(function(root){
  'use strict';
  function escape(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function render(race){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    // Race binding (sibling of the 2026-11-03 ticket-frame mixup): the
    // shared current() slot holds the LAST built race's marks, and
    // background prebuilds for other races overwrite it. When the
    // caller names the page race, a slot owned by a different race
    // renders as unacquired — never as this race's marks.
    if(race&&race.id&&live&&live.raceId&&String(live.raceId)!==String(race.id))
      live={active:false,source:'',unavailable:true,marks:[]};
    var marks=live&&live.active?live.marks:[];
    var historical=live&&live.source==='saved-preoff', stage64=live&&live.source==='stage64-preoff';
    var insufficient=live&&live.unavailable;
    var html=marks.length?marks.map(function(m){
      return '<span class="ai-mark-item">'+escape(m.mark)+' '+escape(m.horseNumber)+' '+escape(m.name)+'</span>';
    }).join('　'):'';
    return '<section id="section-aimarks" class="card"><h2>予想印</h2>'+
      (historical?'<p class="muted">発走前の保存原本（事後再計算なし）</p>':'')+
      (stage64?'<p class="muted">Stage64発走前予想</p>':'')+
      (live&&live.source==='learned-revision-preoff-candidate'?'<p class="muted">検証中の仮印（発走前原本とは別）</p>':'')+
      (live&&live.source==='learned-revision-retrospective'?'<p class="muted">事後再分析の参考印・当時の予想ではありません</p>':'')+
      (insufficient?'<p class="muted">このレースの予想印は未取得です。</p>':'')+
      '<div class="ai-mark-list">'+html+'</div></section>';
  }
  root.ARVEXQMarkFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
