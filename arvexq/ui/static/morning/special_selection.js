/* Fixed special-forecast membership: race identity only, never betting or analysis.
 * Main/graded/Kochi-Final selection is independent from career ingestion.
 */
(function(global){
'use strict';
const VERSION='arvexq-special-race-selection-v1';
const number=x=>Number.isFinite(Number(x))?Number(x):0;
function graded(r){
 if(!r)return false;
 if(r.isGraded===true||r.graded===true||r.isGradeRace===true||r.gradeRace===true)return true;
 const title=String(r.title||''),meta=[r.grade,r.gradeLabel,r.raceGrade,r.gradeCode,
   r.raceClass,r.className,r.category].map(x=>String(x||'')).join(' '),s=title+' '+meta;
 const grade='(?:[ⅠⅡⅢ]|I{1,3}|[123])';
 if(new RegExp('(?:Jpn\\s*)?G\\s*'+grade+'|(?:Jpn\\s*)'+grade+
   '|(?:^|[\\s（(\\[])(?:S|H|M|SP)\\s*'+grade+'(?:$|[\\s）)\\]])|重賞|賞\\s*[（(]重賞[）)]','i').test(s))return true;
 return /(?:ダービー|優駿|グランプリ)(?:$|[（(])/i.test(title);
}
function kochiFinal(r){
 return !!(r&&String(r.track||'')==='高知'&&
   (/ファイナル/i.test(String(r.title||''))||number(r.raceNumber)===12));
}
function mainForTrack(rows){
 const sorted=rows.slice().sort((a,b)=>number(a.raceNumber)-number(b.raceNumber));
 if(!sorted.length)return null;
 return sorted.find(r=>{
   const role=String(r.raceRole||r.role||r.raceType||'').toLowerCase();
   return r.isMain===true||r.mainRace===true||role==='main'||role==='mainrace'||
     /メイン/.test(String(r.title||''));
 })||sorted.find(r=>r.featured===true)||
   sorted.find(r=>number(r.raceNumber)===11)||sorted[sorted.length-1];
}
function select(races){
 const valid=(Array.isArray(races)?races:[]).filter(r=>r&&r.id&&number(r.raceNumber)>0);
 const groups=new Map(),chosen=new Map();
 for(const r of valid){
   const key=[String(r.date||''),String(r.circuit||''),String(r.track||'')].join('|');
   if(!groups.has(key))groups.set(key,[]);
   groups.get(key).push(r);
   if(graded(r)||kochiFinal(r))chosen.set(String(r.id),r);
 }
 for(const rows of groups.values()){
   const main=mainForTrack(rows);
   if(main)chosen.set(String(main.id),main);
 }
 return Array.from(chosen.values()).sort((a,b)=>{
   const ta=String(a.startTime||'99:99'),tb=String(b.startTime||'99:99');
   return ta.localeCompare(tb)||String(a.track||'').localeCompare(String(b.track||''),'ja')||
     number(a.raceNumber)-number(b.raceNumber);
 });
}
global.ARVEXQSpecialSelection=Object.freeze({VERSION,select,graded,kochiFinal,mainForTrack});
})(window);
