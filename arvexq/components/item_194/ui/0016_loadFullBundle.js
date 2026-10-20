function loadFullBundle(d){
  try{
    var raw=localStorage.getItem(fullBundleKey(d));if(!raw)return null;
    var x=JSON.parse(raw);if(!x||!x.body||x.body.complete!==true)return null;
    var age=Date.now()-n(x.ts);
    if(d>=today()&&age>5*60000)return null;
    return x.body
  }catch(e){return null}
}
