/* Immutable morning recommendation evidence. No odds, API writes or result inputs.
 * A published selected race must carry actual validated marks + ticket combos.
 */
(function(global){
'use strict';
const VERSION='arvexq-morning-ticket-evidence-v1';
const TYPES={'ワイド':2,'馬連':2,'馬単':2,'3連複':3,'3連単':3};
const LEVELS=['本線','保険','3連単チャレンジ'];
const MARKS=['','◎','○','▲','☆+','☆','△','注'];
function num(v){return Number.isInteger(Number(v))&&Number(v)>0?Number(v):0}
function capture(r,p,plan,selection){
 if(!r||!r.id||!r.date||!p||!Array.isArray(p.rows)||
    !plan||!plan.betInputGate||plan.betInputGate.ready!==true||
    !['通常買い','強く買う'].includes(plan.decision)||
    !selection||selection.selected!==true)return null;
 const original=p.rows.filter(x=>x&&x.horse&&num(x.horse.horseNumber));
 const known=new Set(),marks=[];
 for(const x of original){
   const no=num(x.horse.horseNumber),mark=String(x.predMark||'');
   if(!no||known.has(no)||!MARKS.includes(mark))return null;
   known.add(no);marks.push({horseNumber:no,mark:mark,singleWinSuitable:!!x.singleWinSuitable});
 }
 if(marks.length<5||marks.filter(x=>x.mark).length<3)return null;
 const axis=marks.filter(x=>x.mark==='◎');
 if(axis.length>1)return null;
 const items=[];
 for(const z of plan.items||[]){
   if(!z||!LEVELS.includes(z.level)||!Object.prototype.hasOwnProperty.call(TYPES,z.kind))continue;
   if(!Array.isArray(z.combos)||!z.combos.length)return null;
   const combos=[];
   for(const raw of z.combos){
     if(!Array.isArray(raw)||raw.length!==TYPES[z.kind])return null;
     const values=raw.map(num);
     if(values.some(n=>!n||!known.has(n))||new Set(values).size!==values.length)return null;
     combos.push(values);
   }
   if(z.kind==='3連単'&&(combos.length<6||combos.length>12))return null;
   items.push({level:z.level,kind:z.kind,combos:combos,points:combos.length,
               reason:String(z.reason||'').slice(0,300)});
 }
 if(!items.some(x=>x.level==='本線'))return null;
 const kinds=[...new Set(items.map(x=>x.kind))];
 if(!Array.isArray(selection.ticketKinds)||selection.ticketKinds.length!==kinds.length||
    !selection.ticketKinds.every(x=>kinds.includes(x)))return null;
 if(!axis.length){
   if(String(selection.primaryType)!=='的中重視型'||
      items.some(x=>!['ワイド','馬連','3連複'].includes(x.kind)))return null;
 }else if(axis.length!==1)return null;
 if(String(selection.primaryType)==='勝ち馬明確型'&&!axis.length)return null;
 return {version:VERSION,raceId:String(r.id),raceDate:String(r.date),fixedAt:'',
    axisStatus:axis.length?'honmei':'no-axis',axisHorseNumber:axis.length?axis[0].horseNumber:0,
    marks:marks,items:items,ticketKinds:kinds,modelVersion:String(plan.engineVersion||plan.betStrategy||'')};
}
function verify(r,e){
 if(!r||!e||e.version!==VERSION||String(e.raceId)!==String(r.id)||
    String(e.raceDate)!==String(r.date)||!e.fixedAt)return false;
 const post=Date.parse(String(r.date)+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00'),
       at=Date.parse(String(e.fixedAt));
 if(!Number.isFinite(post)||!Number.isFinite(at)||at>=post)return false;
 if(!Array.isArray(e.marks)||e.marks.length<5||!Array.isArray(e.items)||!e.items.length)return false;
 const seen=new Set(),axes=[];
 for(const x of e.marks){
   const no=num(x&&x.horseNumber);
   if(!no||seen.has(no)||!MARKS.includes(String(x.mark||'')))return false;
   seen.add(no);if(x.mark==='◎')axes.push(no);
 }
 if(axes.length>1)return false;
 if(e.axisStatus!==(axes.length?'honmei':'no-axis')||
    num(e.axisHorseNumber)!==(axes[0]||0))return false;
 let main=false;const kinds=[];
 for(const x of e.items){
   if(!x||!LEVELS.includes(x.level)||!Object.prototype.hasOwnProperty.call(TYPES,x.kind)||
      !Array.isArray(x.combos)||!x.combos.length)return false;
   if(x.level==='本線')main=true;
   if(!kinds.includes(x.kind))kinds.push(x.kind);
   if(x.kind==='3連単'&&(x.combos.length<6||x.combos.length>12))return false;
   for(const combo of x.combos){
     if(!Array.isArray(combo)||combo.length!==TYPES[x.kind])return false;
     const values=combo.map(num);
     if(values.some(n=>!n||!seen.has(n))||new Set(values).size!==values.length)return false;
   }
 }
 return main&&Array.isArray(e.ticketKinds)&&e.ticketKinds.length===kinds.length&&
   e.ticketKinds.every(x=>kinds.includes(x))&&
   (axes.length>0||e.items.every(x=>['ワイド','馬連','3連複'].includes(x.kind)));
}
function sealedPlan(r,e){
 if(!verify(r,e))return null;
 return {raceId:e.raceId,raceDate:e.raceDate,fixedAt:e.fixedAt,fixedBeforePost:true,
   engineVersion:e.modelVersion||VERSION,decision:'通常買い',
   items:e.items.map(x=>({level:x.level,kind:x.kind,combos:x.combos.map(c=>c.slice()),
     points:x.combos.length,reason:x.reason})),
   primaryKind:e.items.find(x=>x.level==='本線').kind,noAxis:e.axisStatus==='no-axis',
   trifectaReviewed:true,trifectaDecision:e.items.some(x=>x.kind==='3連単')?'採用':'見送り',
   reason:e.origin==='saved-preoff'?'発走前保存の買い目原本。保存時刻の組合せをそのまま復旧しています。':'朝の発走前固定買い目。購入履歴ではなく、事後の組合せ再計算もしていません。',
   dataStatus:'frozen-morning-evidence',referenceBudget:{
     unitYen:100,points:e.items.reduce((a,z)=>a+z.combos.length,0),
     totalYen:e.items.reduce((a,z)=>a+z.combos.length*100,0)}};
}
global.ARVEXQMorningEvidence=Object.freeze({VERSION,capture,verify,sealedPlan});
})(window);
