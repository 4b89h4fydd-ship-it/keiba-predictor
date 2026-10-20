function aiStatsMarkText(row){
  var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
  return (row.marks||[]).slice().sort(function(a,b){return n(order[a.mark],99)-n(order[b.mark],99)||n(a.no)-n(b.no)}).map(function(x){return x.mark+x.no}).join(' ')||'印なし'
}
