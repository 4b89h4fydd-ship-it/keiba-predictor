/* Requirement 58: exclude current and future races from historical evidence. */
(function(root){
  'use strict';
  function normalizeDate(value){
    const s=String(value||'').trim().replace(/\//g,'-').slice(0,10);
    return /^\d{8}$/.test(s)?s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8):s;
  }
  function validDate(value){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    const date=new Date(value+'T00:00:00Z');
    return !Number.isNaN(date.getTime())&&date.toISOString().slice(0,10)===value;
  }
  function beforeRace(runs,race,limit){
    const cutoff=normalizeDate(race&&race.date);
    if(!validDate(cutoff))return [];
    return (Array.isArray(runs)?runs:[]).filter(function(row){
      return row&&typeof row==='object'&&validDate(normalizeDate(row.date||row.raceDate))&&
        normalizeDate(row.date||row.raceDate)<cutoff;
    }).map(function(row){return Object.assign({},row,{date:normalizeDate(row.date||row.raceDate)})})
      .sort(function(a,b){
        return b.date.localeCompare(a.date)||
          Number(b.raceNumber||b.raceNo||0)-Number(a.raceNumber||a.raceNo||0);
      }).slice(0,Number.isInteger(limit)&&limit>=0?limit:5);
  }
  root.ARVEXQPastRunTemporal=Object.freeze({normalizeDate:normalizeDate,beforeRace:beforeRace});
})(typeof window!=='undefined'?window:globalThis);
