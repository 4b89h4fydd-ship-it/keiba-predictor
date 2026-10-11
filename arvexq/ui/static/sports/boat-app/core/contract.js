// SMALL: verified boat-race payload and immutable prediction contract.
export const VENUES=["桐生","戸田","江戸川","平和島","多摩川","浜名湖","蒲郡","常滑","津","三国","びわこ","住之江","尼崎","鳴門","丸亀","児島","宮島","徳山","下関","若松","芦屋","福岡","唐津","大村"];
const ticket=/^[1-6]-[1-6]-[1-6]$/;
export function validTicket(code){
  if(!ticket.test(String(code||"")))return false;
  return new Set(code.split("-")).size===3;
}
export function beforeOff(snapshot,closeAt){
  const a=Date.parse(String(snapshot||"")),b=Date.parse(String(closeAt||""));
  return Number.isFinite(a)&&Number.isFinite(b)&&a<b;
}
export function displayMark(mark){
  if(!mark||typeof mark!=="object")return "—";
  const symbol=String(mark.symbol||"");
  if(!["◎","○","▲","☆","△","注"].includes(symbol))return "—";
  const grade=["A","B","C"].includes(mark.grade)?mark.grade:"";
  if(symbol==="◎"){
    const role=mark.role==="both"?"◎【単】 ◎【軸】":mark.role==="win"?"◎【単】":mark.role==="axis"?"◎【軸】":"◎";
    return role+(grade==="A"?"":grade);
  }
  return symbol;
}
export function usableForecast(race){
  const f=race&&race.forecast;
  if(!f||f.status!=="verified"||!beforeOff(f.snapshotAt,race.closeAt))return false;
  if(!Array.isArray(f.tickets)||f.tickets.length<1||f.tickets.length>6)return false;
  const tickets=f.tickets.map(x=>typeof x==="string"?x:x&&x.combination);
  if(tickets.some(x=>!validTicket(x))||new Set(tickets).size!==tickets.length)return false;
  return Array.isArray(race.entries)&&race.entries.length===6&&
    new Set(race.entries.map(x=>Number(x.boatNo))).size===6&&
    race.entries.every(x=>Number(x.boatNo)>=1&&Number(x.boatNo)<=6&&String(x.name||"").trim());
}
export function selectedRace(race){
  const s=race&&race.selection;
  return !!(usableForecast(race)&&s&&s.approved===true&&
    beforeOff(s.lockedAt,race.closeAt)&&Date.parse(s.lockedAt)<=Date.parse(race.forecast.snapshotAt));
}
export function parseDay(raw,day){
  if(!raw||raw.version!=="arvexq-boat-day-v1"||raw.date!==day||raw.verified!==true||
    !Array.isArray(raw.races))throw Error("検証済みの競艇データがありません");
  const ids=new Set();
  const races=raw.races.filter(r=>{
    if(!r||!VENUES.includes(r.venue)||!Number.isInteger(r.raceNo)||r.raceNo<1||r.raceNo>12||
       !String(r.id||"").startsWith("boat-"+day+"-"))return false;
    if(ids.has(r.id))return false;
    ids.add(r.id);return true;
  });
  return {date:day,races,verifiedAt:String(raw.verifiedAt||"")};
}
export const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
export const todayJst=()=>new Date(Date.now()+9*3600000).toISOString().slice(0,10);
