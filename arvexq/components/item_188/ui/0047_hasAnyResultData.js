function hasAnyResultData(r){return ((r&&r.result||{}).finishers||[]).some(function(x){return n(x&&x.finish)>0})}
