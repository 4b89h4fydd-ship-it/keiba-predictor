function saveFullBundle(d,body){
  try{
    if(!body||body.complete!==true||!(body.races||[]).length||!(body.details||[]).length)return;
    localStorage.setItem(fullBundleKey(d),JSON.stringify({ts:Date.now(),body:body}))
  }catch(e){}
}
