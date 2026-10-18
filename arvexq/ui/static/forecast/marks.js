/* Pure presentation of marks already validated by production prediction adapter. */
(function(root){
  'use strict';
  function visible(row){
    if(!row||row.serverPreoffMark!==true)return '';
    var mark=String(row.predMark||'');
    return ['◎','○','▲','△','☆'].indexOf(mark)>=0?mark:'';
  }
  root.ARVEXQProductionMarks=Object.freeze({visible:visible});
})(typeof window!=='undefined'?window:globalThis);
