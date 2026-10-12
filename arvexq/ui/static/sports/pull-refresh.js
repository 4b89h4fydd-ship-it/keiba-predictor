/* SMALL: one iPhone/Android pull-to-refresh gesture for both ARVEXQ sports. */
(function(root){
  'use strict';
  let installed=false, refreshHandler=null, gesture=null, busy=false, timer=null;
  const THRESHOLD=74;
  const readY=()=>Math.max(0,root.scrollY||0,document.scrollingElement?.scrollTop||0);
  function indicator(){
    let el=document.getElementById('arvexq-pull-refresh');
    if(!el){
      el=document.createElement('div');
      el.id='arvexq-pull-refresh';
      el.className='arv-pull-refresh';
      el.setAttribute('role','status');el.setAttribute('aria-live','polite');
      el.innerHTML='<span class="arv-pull-spinner" aria-hidden="true"></span><b>下に引いて更新</b>';
      document.body.appendChild(el);
    }
    return el;
  }
  function paint(amount=0,message='下に引いて更新',refreshing=false){
    const el=indicator(), ready=amount>=THRESHOLD;
    el.className='arv-pull-refresh'+(amount>0||refreshing?' visible':'')+
      (ready&&!refreshing?' ready':'')+(refreshing?' refreshing':'');
    el.style.setProperty('--pull-y',Math.min(78,Math.max(0,amount*.6))+'px');
    el.querySelector('b').textContent=message;
  }
  function close(){
    busy=false;gesture=null;paint();
    if(timer){clearTimeout(timer);timer=null}
  }
  function trigger(){
    if(busy||typeof refreshHandler!=='function')return;
    busy=true;gesture=null;paint(90,'更新中…',true);
    document.documentElement.dataset.arvexqPullRefreshCount=
      String(1+Number(document.documentElement.dataset.arvexqPullRefreshCount||0));
    let completed=false;
    const finish=()=>{if(completed)return;completed=true;setTimeout(close,450)};
    timer=setTimeout(finish,20000);
    try{Promise.resolve(refreshHandler()).then(finish,finish)}catch(_){finish()}
  }
  function start(e){
    if(busy||e.touches.length!==1)return;
    const target=e.target;
    if(target?.closest?.('button,a,input,select,textarea,[contenteditable="true"]'))return;
    const t=e.touches[0];
    gesture={id:t.identifier,x:t.clientX,y:t.clientY,dy:0,activated:false};
  }
  function move(e){
    if(!gesture||busy)return;
    let t=null;
    for(const candidate of e.touches){if(candidate.identifier===gesture.id){t=candidate;break}}
    if(!t)return;
    const dy=t.clientY-gesture.y, dx=Math.abs(t.clientX-gesture.x);
    if(dx>Math.max(18,dy*.7)||dy<0){gesture=null;paint();return}
    // iOS standalone homes have a fixed sport bar; body scroll can be zero
    // even while nested content scrolls. Only refresh at document's top.
    if(readY()>2){gesture=null;paint();return}
    if(dy<6)return;
    gesture.activated=true;gesture.dy=dy;
    if(e.cancelable)e.preventDefault();
    paint(dy,dy>=THRESHOLD?'離して更新':'下に引いて更新');
  }
  function end(e){
    if(!gesture)return;
    const changed=[...(e.changedTouches||[])];
    if(!changed.some(t=>t.identifier===gesture.id))return;
    const fire=gesture.activated&&gesture.dy>=THRESHOLD&&readY()<=2;
    gesture=null;if(fire)trigger();else paint();
  }
  function mount(options){
    if(typeof options?.refresh!=='function')throw Error('refresh callback required');
    refreshHandler=options.refresh;
    indicator();
    if(installed)return;
    installed=true;
    document.addEventListener('touchstart',start,{passive:true});
    document.addEventListener('touchmove',move,{passive:false});
    document.addEventListener('touchend',end,{passive:true});
    document.addEventListener('touchcancel',()=>{gesture=null;if(!busy)paint()},{passive:true});
  }
  root.ARVEXQPullRefresh=Object.freeze({mount});
})(window);
