/* Read-only observed historic evidence if older D1 payloads lack researchEvidence.
 * No invented lap, speed index, weight, edge, predicted probability or AI rank.
 */
(function(global){
'use strict';
var labels=[
  ['speed','走破能力'],['closing','上がり・持続'],['early','先行・隊列'],
  ['finish','着順実績'],['class','相手レベル'],['form','近況'],
  ['distance','距離適性'],['track','コース適性'],['going','馬場適性'],
  ['surface','芝・ダート適性'],['pedigree','血統'],['connections','騎手・厩舎'],
  ['weight','斤量・馬体'],['draw','枠順・条件変化']];
function observed(r,h){
  if(!r||!h)return null;
  var cutoff=String(r.date||'');
  if(!cutoff)return null;
  var past=(h.allPastRuns||h.recentRaces||[]).filter(function(x){
     return x&&String(x.date||x.raceDate||'')&&String(x.date||x.raceDate)<cutoff;
  }).slice().sort(function(a,b){
     return String(b.date||b.raceDate||'').localeCompare(String(a.date||a.raceDate||''));
  }).slice(0,5);
  function text(value){return value==null||value===''?null:String(value)}
  function num(v,min,max){
    var value=Number(v);return v!=null&&v!==''&&Number.isFinite(value)&&value>=min&&value<=max?value:null;
  }
  function measurement(key,value){return value==null?[]:[{key:key,value:value}]}
  function values(key,items){return[{key:key,measurements:items}]}
  function meanFinish(source){
    var done=source.map(function(x){return num(x.finish||x.finishPosition,1,40)})
       .filter(function(x){return x!=null});
    return done.length?done.length+'走 / 最良'+Math.min.apply(null,done)+'着':null;
  }
  var sections=[],m={};
  past.forEach(function(z){
    var early=num(z.first3FSeconds||z.early3FSeconds||z.early3F,8,90),
        mid=num(z.middle3FSeconds||z.middle3F,8,90),
        late=num(z.last3FSeconds||z.last3F,8,90);
    var pct=num(z.last3FPercentile,0,1);
    sections.push({date:String(z.date||z.raceDate||''),distance:z.distance,
      early3FSeconds:early,middle3FSeconds:mid,late3FSeconds:late,
      last3FWithinRacePercentile:pct});
  });
  m.speed=measurement('代表時計・距離（他レースと単純比較しない）',past.map(function(z){
    var t=num(z.timeSeconds,30,400),d=num(z.distance,400,4000);
    return t&&d?String(t)+'秒/'+d+'m':null;
  }).filter(Boolean).slice(0,2).join(', ')||null);
  m.closing=measurement('同レース上がり相対値',sections.map(function(x){return x.last3FWithinRacePercentile}).filter(function(x){return x!=null}).join(', ')||null);
  m.early=measurement('初角順位（テン実測ではない）',past.map(function(x){
    var corners=x.cornerPositions||[];
    return Array.isArray(corners)&&corners.length?num(corners[0],1,40):null
  }).filter(function(x){return x!=null}).join(', ')||null);
  m.finish=measurement('直近着順',meanFinish(past));
  m.class=measurement('相手レベル（ソースの数値）',past.map(function(x){return num(x.opponentLevel,0,10000)}).filter(function(v){return v!=null}).join(', ')||null);
  m.form=measurement('直近着順',past.map(function(x){return num(x.finish||x.finishPosition,1,40)}).filter(function(v){return v!=null}).join(', ')||null);
  var dist=num(r.distance,400,4000);
  m.distance=measurement('同距離±100mの成績',meanFinish(past.filter(function(x){return dist&&Math.abs(Number(x.distance)-dist)<=100})));
  m.track=measurement('同場成績',meanFinish(past.filter(function(x){return x.track&&r.track&&x.track===r.track})));
  m.going=measurement('同馬場状態の成績',meanFinish(past.filter(function(x){return r.condition&&x.condition===r.condition})));
  m.surface=measurement('同芝ダート実績',meanFinish(past.filter(function(x){return r.surface&&x.surface===r.surface})));
  m.pedigree=measurement('血統',text(h.pedigreeName||h.sireName||h.sire));
  m.connections=measurement('騎手・厩舎名（成績指数ではない）',[text(h.jockey),text(h.trainer)].filter(Boolean).join(' / ')||null);
  m.weight=measurement('当該斤量（実測・発表値）',num(h.carriedWeight,30,75));
  m.draw=measurement('枠番',num(h.frameNumber,1,8));
  return{factors:{version:'race-card-observed-only-v1',items:labels.map(function(x){
    return{key:x[0],label:x[1],measurements:m[x[0]]||[],available:!!(m[x[0]]||[]).length}
  })},sectionals:{runs:sections},status:'read-only-race-card-observed'};
}
global.ARVEXQLocalEvidence=Object.freeze({observed:observed});
})(window);
