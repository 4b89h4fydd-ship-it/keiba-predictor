function saveDetailCache(id,row){try{if(!id||!row||!raceDisplayCoreReady(row,row))return;localStorage.setItem(detailCacheKey(id),JSON.stringify({ts:Date.now(),row:row}))}catch(e){}}
// On upgrade, discard only obsolete device race data, never saved forecasts.
