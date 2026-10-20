function aiStatsCell(label,rows,key,filter){
  var eligible=rows.filter(function(x){return x.eligible&&(!filter||filter(x))}),hits=eligible.filter(function(x){return !!x[key]}).length;
  return '<div><small>'+esc(label)+'</small><strong>'+(eligible.length?Math.round(hits/eligible.length*100)+'%':'—')+'</strong><em>'+hits+'/'+eligible.length+'</em></div>'
}
