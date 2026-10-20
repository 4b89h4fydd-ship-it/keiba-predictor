function installEdgeBack(){
    var gesture=null,suppressClickUntil=0;
    document.addEventListener('touchstart',function(e){
        gesture=null;if(e.touches.length!==1||!canGoBack())return;
        var t=e.touches[0];if(t.clientX>28)return;
        if(e.target.closest&&e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
        gesture={id:t.identifier,x:t.clientX,y:t.clientY,time:Date.now(),locked:false};
    },{passive:true});
    document.addEventListener('touchmove',function(e){
        if(!gesture)return;if(e.touches.length!==1){gesture=null;return}
        var t=e.touches[0],dx=t.clientX-gesture.x,dy=Math.abs(t.clientY-gesture.y);
        if(t.identifier!==gesture.id||dx < -8||(!gesture.locked&&dy>12&&dy>=Math.abs(dx))){gesture=null;return}
        if(dx>12&&dx>dy*1.5)gesture.locked=true;
        if(gesture.locked&&e.cancelable)e.preventDefault();
    },{passive:false});
    document.addEventListener('touchend',function(e){
        var g=gesture;gesture=null;if(!g||e.touches.length)return;
        var t=e.changedTouches[0];if(!t||t.identifier!==g.id)return;
        var dx=t.clientX-g.x,dy=Math.abs(t.clientY-g.y);
        if(dx>=80&&dx>dy*1.5&&Date.now()-g.time<1200){
            if(e.cancelable)e.preventDefault();suppressClickUntil=Date.now()+450;goBack();
        }
    },{passive:false});
    document.addEventListener('touchcancel',function(){gesture=null},{passive:true});
    document.addEventListener('click',function(e){if(Date.now()<suppressClickUntil){e.preventDefault();e.stopImmediatePropagation()}},true);
}

