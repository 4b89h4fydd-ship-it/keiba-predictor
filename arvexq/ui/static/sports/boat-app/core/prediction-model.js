/* SMALL: Mathematical scoring of all ordered three-of-six outcomes.
 * Baseline expert + statistical ensembles, not a fitted/calibrated model.
 */
export const MODEL_VERSION="arvexq-boat-ensemble-v1-experimental";
export const orderedTrifectas=Object.freeze(Array.from({length:6},(_,a)=>
  Array.from({length:6},(_,b)=>Array.from({length:6},(_,c)=>
    a!==b&&b!==c&&a!==c?String(a+1)+"-"+(b+1)+"-"+(c+1):null).filter(Boolean)).flat()).flat());
const finite=(x,a,b)=>typeof x==="number"&&Number.isFinite(x)?Math.min(b,Math.max(a,x)):null;
const normalized=(x,a,b,defaultValue=.5)=>x===null?defaultValue:Math.min(1,Math.max(0,(x-a)/(b-a)));
const rate=x=>typeof x==="number"&&Number.isFinite(x)?Math.min(1,Math.max(0,x>1?x/100:x)):null;
const avg=(xs,fb=.5)=>{const f=xs.filter(x=>Number.isFinite(x));return f.length?f.reduce((s,x)=>s+x,0)/f.length:fb};
export function featureScores(entrants,context={}){
  if(!Array.isArray(entrants)||entrants.length!==6||
     new Set(entrants.map(x=>x?.boatNo)).size!==6||
     entrants.some(x=>!Number.isInteger(x?.boatNo)||x.boatNo<1||x.boatNo>6))throw Error("6艇の検証済み出走選手が必要です");
  return [...entrants].sort((a,b)=>a.boatNo-b.boatNo).map((e,i)=>{
    const p=e.player||{},m=e.motor||{},ex=e.exhibition||{};
    const skill=avg([rate(p.winRate),rate(p.top3Rate),rate(p.localWinRate),rate(p.courseWinRate),rate(p.courseTop3Rate)]);
    const start=avg([normalized(finite(p.avgST,0,.4),.35,.08),normalized(finite(p.courseAvgST,0,.4),.35,.08)]);
    const motor=avg([rate(m.top2Rate),rate(m.top3Rate)]);
    const exhibition=avg([normalized(finite(ex.time,6,9),8,6),normalized(finite(ex.turnTime,3,9),8,4),normalized(finite(ex.straightTime,3,9),8,4)]);
    const course=Number.isInteger(e.expectedCourse)&&e.expectedCourse>=1&&e.expectedCourse<=6?e.expectedCourse:i+1;
    const coursePrior=[.85,.65,.52,.43,.36,.30][course-1],penalty=p.hasF===true?.07:0;
    const expert=.28*skill+.18*start+.17*motor+.17*exhibition+.20*coursePrior-penalty;
    const statistical=.4*skill+.18*start+.12*motor+.10*exhibition+.20*coursePrior-penalty;
    return {boatNo:e.boatNo,course,skill,start,motor,exhibition,
      score:Math.exp(2.7*(.58*expert+.42*statistical)),expert,statistical};
  });
}
export function outcomeProbabilities(entries,context={}){
  const strengths=featureScores(entries,context);
  const res=orderedTrifectas.map(combination=>{
    const order=combination.split("-").map(Number);
    let remaining=strengths.map(x=>x.score),p=1;
    for(const boat of order){
      const sum=remaining.reduce((a,b)=>a+b,0),w=remaining[boat-1];
      p*=w/sum;remaining[boat-1]=0;
    }
    return {combination,p};
  });
  const sum=res.reduce((a,b)=>a+b.p,0);
  return res.map(r=>({...r,p:r.p/sum})).sort((a,b)=>b.p-a.p||a.combination.localeCompare(b.combination));
}
export function marginalProbabilities(outcomes){
  const agg=Array.from({length:6},(_,i)=>({boatNo:i+1,win:0,top3:0,second:0,third:0}));
  for(const {combination,p} of outcomes){
    const order=combination.split("-").map(Number);
    order.forEach((n,i)=>{agg[n-1].top3+=p;if(i===0)agg[n-1].win+=p;else if(i===1)agg[n-1].second+=p;else agg[n-1].third+=p});
  }
  return agg;
}
export function predictionMarks(outcomes,{calibrated=false}={}){
  const m=marginalProbabilities(outcomes);
  const rank=[...m].sort((a,b)=>(.55*b.win+.45*b.top3/3)-(.55*a.win+.45*a.top3/3));
  const winner=[...m].sort((a,b)=>b.win-a.win)[0],axis=[...m].sort((a,b)=>b.top3-a.top3)[0];
  const symbols=["◎","○","▲","☆","△","注"],marks={};
  for(const row of rank){
    const priority=rank.indexOf(row),role=row.boatNo===winner.boatNo&&row.boatNo===axis.boatNo?"both":
      row.boatNo===winner.boatNo?"win":row.boatNo===axis.boatNo?"axis":"none";
    const grade=calibrated&&(row.win>=.48||row.top3>=.85)?"A":
      calibrated&&(row.win>=.28||row.top3>=.68)?"B":"C";
    marks[row.boatNo]={symbol:priority===0||role!=="none"?"◎":symbols[priority],
      role,grade,winProbability:row.win,top3Probability:row.top3};
  }
  return marks;
}
