function immutableStoredAiBetView(r,plan){
  // A post-lock cancellation or scratch is a display warning, not a license
  // to erase the historical pre-off ticket or silently revise its selections.
  if(!plan)return null;
  var status=String(r&&r.raceStatus||'')+' '+String(r&&r.result&&r.result.status||'');
  var scratched={};(r&&r.horses||[]).forEach(function(h){if(isScratchHorse(h))scratched[n(h.horseNumber)]=1});
  var affected=(plan.items||[]).some(function(z){return (z.combos||[]).some(function(c){return (c||[]).some(function(no){return !!scratched[n(no)]})})});
  if(/中止|取止|取り止め|不成立/.test(status))return Object.assign({},plan,{postLockNotice:'レース中止・取止め。発走前の買い目を記録として表示しています（投票可否・返還は公式情報で確認）。'});
  if(affected)return Object.assign({},plan,{postLockNotice:'固定後に取消・除外馬が発生。発走前の買い目は変更せず記録として表示します。'});
  return plan
}
