function normalizeInitialAppLaunch(){
  try{
    var standalone=!!((window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches)||window.navigator.standalone===true);
    if(!standalone)return;
    var u=new URL(window.location.href),t=today(),d=u.searchParams.get('date');
    // A fresh ARVEXQ app launch always starts from today's home. Historical
    // navigation inside the running app is still preserved and has the 今日へ button.
    if(d&&d!==t){
      u.searchParams.set('date',t);
      ['race_id','track','picker','horse','tab','home','pick_circuit','ai_track'].forEach(function(k){u.searchParams.delete(k)});
      window.history.replaceState({},'',u.pathname+(u.searchParams.toString()?'?'+u.searchParams.toString():'')+u.hash);
    }
  }catch(e){}
}
