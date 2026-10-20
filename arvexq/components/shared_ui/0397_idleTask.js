function idleTask(fn,delay){
  delay=n(delay,1200);
  if(window.requestIdleCallback){
    setTimeout(function(){requestIdleCallback(function(){try{fn()}catch(e){}},{timeout:1800})},delay)
  }else setTimeout(function(){try{fn()}catch(e){}},delay)
}

