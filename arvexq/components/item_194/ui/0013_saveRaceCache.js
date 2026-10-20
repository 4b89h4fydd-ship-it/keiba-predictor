function saveRaceCache(d,c,rows){try{localStorage.setItem(cacheKey(d,c),JSON.stringify({ts:Date.now(),rows:rows}))}catch(e){}}
