/* Pure presentation of marks already validated by production prediction adapter. */
(function(root){
  'use strict';
  function visible(row){
    if(!row||row.serverPreoffMark!==true&&row.originalPreoffMark!==true)return '';
    var mark=String(row.predMark||'');
    return ['◎','○','▲','△','☆','☆+','注'].indexOf(mark)>=0?mark:'';
  }
  root.ARVEXQProductionMarks=Object.freeze({visible:visible});
})(typeof window!=='undefined'?window:globalThis);
