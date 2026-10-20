function installPwaCache(){
  // Online-first stability: stale service workers were intercepting fresh v329
  // assets/API navigation on iPhone. Unregister them and use normal HTTP cache.
  try{
    if("serviceWorker" in navigator){
      navigator.serviceWorker.getRegistrations().then(function(rs){
        return Promise.all(rs.map(function(r){try{return r.unregister()}catch(e){return false}}))
      }).catch(function(){})
    }
    if("caches" in window){
      caches.keys().then(function(keys){
        return Promise.all(keys.map(function(k){return caches.delete(k)}))
      }).catch(function(){})
    }
  }catch(e){}
}
