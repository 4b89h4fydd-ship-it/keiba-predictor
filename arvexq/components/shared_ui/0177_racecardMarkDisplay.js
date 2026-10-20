function racecardMarkDisplay(mark){
  var raw=String(mark||'—').trim(),pair=/^([◎○▲☆△注])([+＋])$/.exec(raw);
  if(pair){
    return '<span class="rc-mark-stack" aria-hidden="true"><span class="rc-mark-top">'+esc(pair[1])+'</span><span class="rc-mark-bottom">＋</span></span>';
  }
  return esc(raw);
}

