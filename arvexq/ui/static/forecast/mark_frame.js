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
    var stage64=live&&live.source==='stage64-provisional';
    var insufficient=live&&live.unavailable;
    var html=marks.length?marks.map(function(m){
      var label=stage64&&m.stage64Provisional
        ?(m.role==='win-axis'?'◎【単】◎【軸】'
         :(m.role==='axis'?'◎【軸】':(m.role==='win'?'◎【単】':m.mark)))
        :m.mark;
      return '<span class="ai-mark-item">'+escape(label)+' '+escape(m.horseNumber)+' '+escape(m.name)+'</span>';
    }).join('　'):'';
    return '<section id="section-aimarks" class="card"><h2>予想印</h2>'+
      (historical?'<p class="muted">発走前の保存原本（事後再計算なし）</p>':'')+
      (stage64?'<p class="muted">Stage64 ◎【単】・◎【軸】候補。A/B/C評価・的中率は未検証です。</p>':'')+
      (insufficient?'<p class="muted">未承認の予想印は削除済みです。</p>':'')+
      '<div class="ai-mark-list">'+html+'</div></section>';
  }
  root.ARVEXQMarkFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
