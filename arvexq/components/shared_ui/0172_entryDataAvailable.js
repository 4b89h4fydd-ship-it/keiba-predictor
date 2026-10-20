function entryDataAvailable(r){return !!(r&&(r.horses||[]).some(function(h){return h&&n(h.horseNumber)>0&&String(h.name||'').trim()}))}
