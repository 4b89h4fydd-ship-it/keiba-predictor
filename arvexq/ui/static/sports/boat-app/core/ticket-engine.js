/* SMALL: Formation parser and verified quote/ticket reconciliation. */
import {validTicket} from "./contract.js";
import {orderedTrifectas,marginalProbabilities,predictionMarks,MODEL_VERSION} from "./prediction-model.js";
const probability=v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=1;
export function expandFormation(format){
  const parts=String(format||"").replace(/\s/g,"").split("-");
  if(parts.length!==3||parts.some(p=>!/^[1-6]+$/.test(p)))throw Error("各着順には1〜6を指定してください");
  const res=[];
  for(const a of parts[0])for(const b of parts[1])for(const c of parts[2]){
    const t=a+"-"+b+"-"+c;
    if(validTicket(t)&&!res.includes(t))res.push(t);
  }
  if(!res.length)throw Error("成立する3連単の買い目がありません");
  return res;
}
export function oddsQuote(race,code){
  if(!validTicket(code))return null;
  const o=race?.odds3t;
  if(!o||o.verified!==true||!["BOATRACE公式","正規許諾フィード"].includes(o.source)||
     !Number.isFinite(Date.parse(o.updatedAt||""))||!o.values||typeof o.values!=="object")return null;
  const raw=o.values[code];
  const value=Number(raw);
  return raw!==null&&raw!==undefined&&Number.isFinite(value)&&value>=1&&value<=100000?value:null;
}
export function chooseTickets(outcomes,race,{limit=6,minOdds=1,maxOdds=10000,mode="balanced"}={}){
  if(!Array.isArray(outcomes)||outcomes.length!==120||!outcomes.every(x=>validTicket(x.combination)&&probability(x.p))||
     Math.abs(outcomes.reduce((s,x)=>s+x.p,0)-1)>.000001)throw Error("120組の正規化確率が必要です");
  if(!Number.isInteger(limit)||limit<1||limit>6)throw Error("買い目は最大6点");
  const ranking=outcomes.map(x=>{
    const odds=oddsQuote(race,x.combination);
    const available=odds!==null&&odds>=minOdds&&odds<=maxOdds;
    // These are *uncalibrated* theoretical ranks, not measured EV or
    // reliable predicted ROI. Prefer probability and consider odds once present.
    const score=mode==="high-payout"?x.p*Math.sqrt(available?odds:1):
      x.p*(available?Math.min(1.8,Math.sqrt(odds)/3):1);
    return {...x,odds,score,quoteAt:odds!==null?race.odds3t.updatedAt:null};
  });
  return ranking.filter(x=>mode!=="high-payout"||x.odds!==null)
    .sort((a,b)=>b.score-a.score||b.p-a.p).slice(0,limit);
}
export function summarizeFormation(tickets){
  const codes=tickets.map(t=>typeof t==="string"?t:t.combination);
  if(codes.length===0||codes.length>6||codes.some(c=>!validTicket(c))||
     new Set(codes).size!==codes.length)return null;
  const a=[...new Set(codes.map(x=>x[0]))].sort().join("");
  const b=[...new Set(codes.map(x=>x[2]))].sort().join("");
  const c=[...new Set(codes.map(x=>x[4]))].sort().join("");
  const form=a+"-"+b+"-"+c;
  try{
    const actual=expandFormation(form);
    if(actual.length===codes.length&&codes.every(x=>actual.includes(x)))return form;
  }catch(_){}
  return null;
}
export function experimentalForecast(entries,race,probabilities,opts={}){
  const marks=predictionMarks(probabilities,{calibrated:false});
  const tickets=chooseTickets(probabilities,race,opts);
  return {status:"experimental",model:MODEL_VERSION,marks,tickets,
    warning:"過去データによる時間順校正前の試験予想です。配信確定データには使用しません。"};
}
export function inputQuality(race){
  if(!Array.isArray(race?.entries)||race.entries.length!==6)return {ready:false,issues:["出走表未取得"]};
  const issues=[],now=Date.parse(race?.closeAt||"");
  if(!Number.isFinite(now))issues.push("締切時刻未取得");
  const entrants=race.entries;
  if(entrants.some(e=>!e.name||!Number.isInteger(e.boatNo)))issues.push("選手情報不足");
  if(entrants.some(e=>!e.player?.winRate||!e.motor?.top2Rate))issues.push("選手・モーターデータ不足");
  if(!race?.odds3t?.verified)issues.push("公式3連単オッズ未取得");
  return {ready:issues.length===0,issues};
}
