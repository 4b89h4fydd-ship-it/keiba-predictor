function copyCurrentBet(){
  if(!state.race)return;var p=state.pred||predict(state.race),text=betTransferText(state.race,p);
  if(!text){setBetCopyStatus('買い目がまだありません');return}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(function(){setBetCopyStatus('買い目をコピーしました')}).catch(function(){setBetCopyStatus(fallbackCopyText(text)?'買い目をコピーしました':'コピーできませんでした')})}
  else setBetCopyStatus(fallbackCopyText(text)?'買い目をコピーしました':'コピーできませんでした')
}
// Dedicated betting display: /betting/bet_view.js
