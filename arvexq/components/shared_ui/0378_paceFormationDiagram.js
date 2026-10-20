function paceFormationDiagram(r,p,cfg){
  var pack=paceStagePack(p,cfg.visualKey),byNo={};
  (r.horses||[]).forEach(function(h){byNo[n(h.horseNumber)]=h});
  if(!pack.length)return '<div class="empty pace-stage-empty">隊列図を準備中です。</div>';
  var height=Math.max(330,112+Math.max(0,pack.length-1)*27),span=Math.max(1,pack.length-1);
  return '<section class="pace-formation-card">'
    +'<div class="pace-formation-head"><b>隊列図</b><span>'+(cfg.key==='start'?'ハナ争い後の収まり想定':'上が前方・下が後方')+'</span></div>'
    +'<button type="button" class="pace-formation-next" data-pace-next="'+((cfg.index+1)%PACE_STAGE_PAGES.length)+'" aria-label="隊列図をタップして次の局面へ：'+esc(PACE_STAGE_PAGES[(cfg.index+1)%PACE_STAGE_PAGES.length].label)+'">'
    +'<div class="pace-lane-axis"><span>内</span><b>想定進路</b><span>外</span></div>'
    +'<div class="pace-formation-track" style="height:'+height+'px">'
      +'<div class="pace-front-arrow">前方 ↑</div>'
      +'<div class="pace-center-line" aria-hidden="true"></div>'
      +pack.map(function(z,idx){
        var no=n(z.no),h=byNo[no]||{},fr=clamp(n(h.frameNumber,no),1,8),lane=clamp(n(z.lane,0),-3,3),
            left=50+lane*9,top=52+(height-100)*(idx/span),rankLabel=idx===0?'ハナ':(idx===1?'2番手':String(idx+1));
        return '<div class="pace-horse-node" style="left:'+left+'%;top:'+Math.round(top)+'px" aria-label="'+esc(rankLabel+' '+no+'番 '+(h.name||''))+'">'
          +'<span class="pace-rank-label">'+esc(rankLabel)+'</span><i class="pace-horse-dot frame'+fr+'">'+esc(no)+'</i></div>'
      }).join('')
      +'<div class="pace-rear-label">後方</div>'
    +'</div><div class="pace-formation-tap-hint">図をタップ：次の局面 '+esc(PACE_STAGE_PAGES[(cfg.index+1)%PACE_STAGE_PAGES.length].label)+' ›</div></button>'
    +(cfg.key==='start'?'<div class="pace-diagram-note">ハナ争いは説明文、図は争いが収まった直後の隊列を表示。</div>':'')
    +'</section>'
}
