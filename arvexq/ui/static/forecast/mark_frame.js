/* Read-only symbol display of authorized server prediction; no ranking here. */
(function(root){
  'use strict';
  function escape(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var marks=live&&live.active?live.marks:[];
    var historical=live&&live.source==='saved-preoff';
    var insufficient=live&&live.unavailable;
    var retrospective=live&&live.source==='postrace-reference';
    var html=marks.length?marks.map(function(m){
      return '<span class="ai-mark-item">'+escape(m.mark)+' '+escape(m.horseNumber)+' '+escape(m.name)+'</span>';
    }).join('　'):'';
    return '<section id="section-aimarks" class="card"><h2>予想印</h2>'+
      (historical?'<p class="muted">発走前の保存原本（事後再計算なし）</p>':'')+
      (retrospective?'<p class="muted">10/18の事後参考再計算。発走前予想・的中実績ではありません。</p>':'')+
      (insufficient?'<p class="muted">データ不足・印の再計算不可</p>':'')+
      '<div class="ai-mark-list">'+html+'</div></section>';
  }
  root.ARVEXQMarkFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
