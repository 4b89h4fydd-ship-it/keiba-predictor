/* Requirement 55: reconcile duplicate historical observations without mutating source evidence. */
(function(root){
  'use strict';
  function number(value){const n=Number(value);return Number.isFinite(n)?n:0}
  function normalizedDate(value){
    const s=String(value||'').trim().replace(/\//g,'-').slice(0,10);
    return /^\d{8}$/.test(s)?s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8):s;
  }
  function merge(horse){
    const h=horse||{},seen=new Map(),out=[];
    const recent=Array.isArray(h.recentRaces)?h.recentRaces:[];
    const all=Array.isArray(h.allPastRuns)?h.allPastRuns:[];
    for(const row of recent.concat(all)){
      if(!row||typeof row!=='object'||Array.isArray(row))continue;
      const date=normalizedDate(row.date||row.raceDate);
      const raceNo=number(row.raceNumber||row.raceNo);
      const key=[date,String(row.track||''),number(row.distance),raceNo].join('|');
      if(!seen.has(key)){
        const copy=Object.assign({},row,{date});
        if(Array.isArray(row.cornerPositions))copy.cornerPositions=row.cornerPositions.slice();
        seen.set(key,copy);out.push(copy);continue;
      }
      const prior=seen.get(key);
      const corners=Array.isArray(prior.cornerPositions)?prior.cornerPositions.slice():[];
      (Array.isArray(row.cornerPositions)?row.cornerPositions:[]).forEach(function(value,i){
        if(number(corners[i])<=0&&number(value)>0)corners[i]=value;
      });
      if(corners.length)prior.cornerPositions=corners;
      if(!prior.earlyTiming&&row.earlyTiming&&typeof row.earlyTiming==='object')
        prior.earlyTiming=Object.assign({},row.earlyTiming);
      if(!number(prior.finish)&&number(row.finish))prior.finish=row.finish;
      for(const name of ['timeBehindWinner','marginSeconds','marginEvidenceSource',
        'marginEvidence','opponentLevel','surface','distance','raceNumber']){
        if((prior[name]==null||prior[name]==='')&&row[name]!=null&&row[name]!=='')
          prior[name]=row[name];
      }
    }
    return out;
  }
  root.ARVEXQPastRunDeduplicate=Object.freeze({merge:merge});
})(typeof window!=='undefined'?window:globalThis);
