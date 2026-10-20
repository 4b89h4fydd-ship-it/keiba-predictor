function paceStageEvidence(p,cfg){
  return '<section class="pace-stage-explain"><h2>'+esc(cfg.detail)+'</h2>'
    +'<p class="pace-stage-narrative">'+esc(paceStageNarrative(p,cfg.key))+'</p>'
    +(cfg.key==='start'?'<p class="muted">先行の基本根拠は過去5走の初角位置。取得元付きの個別テン1F・ゲート反応・初動加速データがある場合のみ弱い補正に使用します。個別センサーは提供測定値、映像解析は推定値、公式レースラップは先頭馬の区間時計です。データが無い馬は実測値を表示しません。</p>':'')
    +'</section>'
}
