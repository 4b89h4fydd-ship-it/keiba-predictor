function markRoleLabel(x){
  if(!x||x.predMark!=='◎')return '';
  if(x.markFrozen&&x.honmeiRole==='axis')return '保存印：◎（旧軸）';
  if(x.markFrozen&&x.honmeiRole==='win')return '保存印：◎（旧単勝）';
  return x.markFrozen&&x.honmeiRole!=='win-axis'?'保存印：◎':'◎ 本命';
}
