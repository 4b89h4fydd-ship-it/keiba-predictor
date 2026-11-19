'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={};context.window=context;vm.createContext(context);
function load(p){vm.runInContext(fs.readFileSync(p,'utf8'),context,{filename:p});}
load('arvexq/ui/static/morning/frozen_ticket_evidence.js');
for(const name of ['prediction','marks','tickets','prediction_frame','mark_frame','ticket_frame'])
  load('arvexq/ui/static/forecast/'+name+'.js');

const triples=[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]];
const receipt={
 version:'arvexq-morning-ticket-evidence-v1',
 raceId:'jra-2099-12-31-阪神-11',raceDate:'2099-12-31',
 fixedAt:'2099-12-31T09:10:00+09:00',axisStatus:'honmei',axisHorseNumber:1,
 marks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},
   {horseNumber:3,mark:'▲'},{horseNumber:4,mark:'△'},{horseNumber:5,mark:'☆'}],
 items:[
   {level:'本線',kind:'馬連',combos:[[1,2],[1,3]],reason:'専門紙原本'},
   {level:'3連単チャレンジ',kind:'3連単',combos:triples,reason:'<unsafe>'}
 ],
 ticketKinds:['馬連','3連単'],modelVersion:'approved-recorded-original'
};
const race={
 id:receipt.raceId,date:receipt.raceDate,startTime:'23:50',
 horses:receipt.marks.map((m)=>({horseNumber:m.horseNumber,name:'Horse '+m.horseNumber})),
 morningTicketEvidence:receipt
};
const original=JSON.stringify(race);
assert.equal(context.ARVEXQMorningEvidence.verify(race,receipt),true);
const shown=context.ARVEXQProductionTickets.build(race);
assert.equal(shown.fixedAt,receipt.fixedAt);
assert.equal(shown.items.length,2);
assert.equal(JSON.stringify(shown.items[0].combos),JSON.stringify([[1,2],[1,3]]));
assert.equal(JSON.stringify(shown.items[1].combos),JSON.stringify(triples));
const frame=context.ARVEXQTicketFrame.contents(race);
// Heading lives in the composed view (render's h2 / the bets tab's
// top bar) since the 2026-11-04 grouping rework removed the doubled
// in-contents titles; contents itself carries no heading any more.
assert.match(context.ARVEXQTicketFrame.render(race),/おすすめ買い目/);
assert.doesNotMatch(frame,/おすすめ買い目/);
// The aggregated display (2026-11-19) no longer enumerates every
// combination as a chip: a group may render as a formation, a box, a
// box with named exceptions (BOX minus the 除く combinations), an
// axis flow, an axis-multi, grouped head lines, or plain chips. The
// guarantee protected here is not a notation but the set itself:
// decoding each rendered ticket block must reproduce exactly the
// sealed original's combinations for that kind. (The retired literal
// checks /1-2\.3/ and /1\.2\.3-1\.2\.3-1\.2\.3/ pinned the pre-
// aggregation axis/formation spellings of these two groups.)
const KIND_LEN={'馬連':2,'ワイド':2,'馬単':2,'3連複':3,'3連単':3};
const ORDERED_KIND={'3連単':1,'馬単':1};
function chooseFrom(arr,k){
  const out=[];
  (function rec(s,cur){if(cur.length===k){out.push(cur.slice());return;}
    for(let i=s;i<arr.length;i++){cur.push(arr[i]);rec(i+1,cur);cur.pop();}})(0,[]);
  return out;
}
function decodeCombosHtml(html,kind){
  const len=KIND_LEN[kind],ordered=!!ORDERED_KIND[kind];
  const summary=html.match(/<span class="arv-three-combo arv-three-summary">([^<]+)<\/span>/);
  if(summary){
    const text=summary[1];
    if(html.includes('arv-three-box-label')){
      const members=text.split('.').map(Number);
      let combos=chooseFrom(members,len);
      const except=html.match(/<span class="arv-three-except">除く：([^<]+)<\/span>/);
      if(except){
        const missing=new Set(except[1].split('、').map(s=>
          s.split(' - ').map(Number).sort((a,b)=>a-b).join(',')));
        combos=combos.filter(c=>!missing.has(c.slice().sort((a,b)=>a-b).join(',')));
      }
      return combos;
    }
    if(html.includes('arv-three-axis-label')){
      const [axisText,partnerText]=text.split(' - ');
      const axis=Number(axisText);
      return partnerText.split('・').map(Number).flatMap(p=>[[axis,p],[p,axis]]);
    }
    if(ordered){
      const legs=text.split('-').map(part=>part.split('.').map(Number));
      const out=[];
      (function gen(pos,cur,used){
        if(pos===legs.length){out.push(cur.slice());return;}
        legs[pos].forEach(n=>{if(!used[n]){used[n]=1;cur.push(n);
          gen(pos+1,cur,used);cur.pop();used[n]=0;}});
      })(0,[],{});
      return out;
    }
    const [axisText,partnerText]=text.split('-');
    const axis=axisText.split('.').map(Number);
    const partners=partnerText.split('.').map(Number);
    return chooseFrom(partners,len-axis.length).map(rest=>axis.concat(rest));
  }
  const combos=[];
  const spanRe=/<span class="arv-three-combo[^"]*">([\s\S]*?)<\/span>/g;
  let m;
  while((m=spanRe.exec(html))!==null){
    const inner=m[1];
    const line=inner.match(/<b class="arv-three-line-head">([^<]+)<\/b><span class="arv-three-line-sep">[^<]*<\/span>([^<]+)$/);
    if(line){
      const head=line[1].split(ordered?' → ':'・').map(Number);
      line[2].split('、').map(Number).forEach(t=>combos.push(head.concat(t)));
    }else combos.push(inner.split(' - ').map(Number));
  }
  return combos;
}
function renderedCombosByKind(frameHtml){
  const byKind={};
  for(const segment of frameHtml.split('<div class="arv-three-ticket">').slice(1)){
    const head=segment.match(/<div class="arv-three-ticket-head"><b>([^<]+)<\/b>/);
    const strong=segment.match(/<strong class="arv-three-combos">([\s\S]*?)<\/strong>/);
    if(head&&strong)byKind[head[1]]=decodeCombosHtml(strong[1],head[1]);
  }
  return byKind;
}
const renderedByKind=renderedCombosByKind(frame);
for(const item of receipt.items){
  const keyOf=ORDERED_KIND[item.kind]
    ? (c=>c.join(','))
    : (c=>c.slice().sort((a,b)=>a-b).join(','));
  const want=item.combos.map(keyOf).sort();
  const got=(renderedByKind[item.kind]||[]).map(keyOf).sort();
  assert.deepEqual(got,want,'rendered '+item.kind+' must decode to the sealed original combinations');
}
assert.match(frame,/8点|2点/);
assert.doesNotMatch(frame,/<unsafe>/);
assert.equal(JSON.stringify(race),original);

for(const malformed of [
  {...race, id:'different-race'},
  {...race,date:'2099-12-30'},
  {...race, morningTicketEvidence:{...receipt,fixedAt:'2100-01-01T00:00:00+09:00'}},
  {...race, morningTicketEvidence:{...receipt,items:[{level:'本線',kind:'馬連',combos:[[1,99]]}],ticketKinds:['馬連']}},
  {...race,morningTicketEvidence:null}
]){
 const item=context.ARVEXQProductionTickets.build(malformed);
 assert.equal(item.items.length,0);
 assert.doesNotMatch(context.ARVEXQTicketFrame.render(malformed),/1\.2\.3-1\.2\.3-1\.2\.3/);
}

 // Only timestamp-verified genuine frozen originals can be displayed; invented marks are rejected.
 // Exercise the same adapter for 92 distinct race IDs, not only selected UI cards.
const originalDay='2026-10-18';
for(let k=0;k<92;k++){
  const id=(k%2?'nar':'jra')+'-2026-10-18-venue'+k+'-race'+k;
  const fixed={...receipt,raceId:id,raceDate:originalDay,fixedAt:'2026-10-18T07:10:00+09:00'};
  const originalRace={...race,id,date:originalDay,startTime:'12:00',circuit:k%2?'地方':'中央',
    morningTicketEvidence:fixed};
  assert.equal(context.ARVEXQMorningEvidence.verify(originalRace,fixed),true);
  const preserved=context.ARVEXQProductionPrediction.build(originalRace);
  assert.equal(context.ARVEXQProductionPrediction.current().source,'saved-preoff');
  assert.deepEqual(Array.from(preserved.rows,x=>x.predMark),['◎','○','▲','△','☆']);
  assert.equal(context.ARVEXQProductionPrediction.current().unavailable,false);
  assert.equal(context.ARVEXQProductionMarks.visible(preserved.rows[0]),'◎');
  assert.equal(preserved.rows[0].winProbability,null);
  assert.match(context.ARVEXQMarkFrame.render(),/発走前の保存原本/);
  assert.match(context.ARVEXQPredictionFrame.render(),/発走前保存の原本/);
  const bet=context.ARVEXQProductionTickets.current();
  assert.equal(bet.items.length,2);
  assert.equal(JSON.stringify(bet.items[1].combos),JSON.stringify(triples));
}
// The same verified archive is allowed in existing nested daily summaries.
const nestedEvidence={...receipt,raceId:'test-nested-2026-10-18',raceDate:originalDay,
 fixedAt:'2026-10-18T07:10:00+09:00'};
const nestedRace={...race,id:nestedEvidence.raceId,date:originalDay,startTime:'12:00',
 morningTicketEvidence:null,
 volatility:{morningPicks:{ticketEvidence:nestedEvidence}}};
assert.equal(context.ARVEXQProductionPrediction.build(nestedRace).rows[0].predMark,'◎');
assert.equal(context.ARVEXQProductionTickets.build(nestedRace).items.length,2);
// No saved original, wrong roster or a receipt sealed after the post: no historical marks.
for(const bad of [
 {...nestedRace,volatility:{}},
 {...nestedRace,horses:nestedRace.horses.slice(1)},
 {...nestedRace,volatility:{morningPicks:{ticketEvidence:{
    ...nestedEvidence,fixedAt:'2026-10-18T12:10:00+09:00'}}}},
 {...nestedRace,id:'another-race'},
]){
 const row=context.ARVEXQProductionPrediction.build(bad).rows[0];
 assert.equal(row.predMark,'');
 assert.equal(context.ARVEXQProductionTickets.build(bad).items.length,0);
}

console.log('VERIFIED_ORIGINAL_TICKETS_RENDERED_UNCHANGED_AND_INVALIDS_REJECTED');
