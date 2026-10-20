function loadStoredAiBet(id){
  // Only the current device receipt key is eligible for live presentation.
  // Legacy v180-v218 receipts remain untouched in storage for external audit.
  try{
    var x=JSON.parse(localStorage.getItem(aiBetStoreKey(id))||'null');
    return x&&((x.items&&x.items.length)||x.decision==='見送り')?x:null;
  }catch(e){return null}
}
