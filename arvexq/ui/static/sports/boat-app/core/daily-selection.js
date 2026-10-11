/* SMALL: once-per-morning publication target; no retrospective selections.
 * High payout is a possibility, never a guaranteed result or guaranteed profit.
 * Only independently calibrated forecasts qualify.
 */
import {usableForecast,beforeOff,selectedRace} from "./contract.js";
import {oddsQuote} from "./ticket-engine.js";
export const HIGHLIGHT_MIN_ODDS=15;
export function eligibleHighPayout(race){
  if(!usableForecast(race)||race?.forecast?.calibration?.validated!==true)return false;
  const f=race.forecast;
  if(!beforeOff(f.snapshotAt,race.closeAt))return false;
  if(!Array.isArray(f.probabilities)||f.probabilities.length!==120)return false;
  const prob=new Map(f.probabilities.map(t=>[t.combination,t.probability]));
  if(prob.size!==120||[...prob.values()].some(x=>typeof x!=="number"||!Number.isFinite(x)||x<0||x>1)||
     Math.abs([...prob.values()].reduce((a,b)=>a+b,0)-1)>0.001)return false;
  const tickets=f.tickets.map(t=>typeof t==="string"?{combination:t}:t);
  const outcome=tickets.map(t=>({code:t.combination,odds:oddsQuote(race,t.combination),prob:prob.get(t.combination)}));
  // One realistic high-dividend candidate inside the fixed <=6 tickets.
  // Do NOT treat mere odds >=15x as evidence of a positive expected value.
  return outcome.some(x=>x.odds!==null&&x.odds>=HIGHLIGHT_MIN_ODDS&&x.prob>0&&x.prob*x.odds>=1);
}
export function dailyRecommendations(races,date){
  const safe=(races||[]).filter(r=>r&&r.id&&String(r.id).startsWith("boat-"+date+"-"));
  // "Morning" selections must be locked independently in a fixed record.
  const selected=safe.filter(r=>selectedRace(r)&&eligibleHighPayout(r)).sort(
    (a,b)=>String(a.selection.lockedAt).localeCompare(String(b.selection.lockedAt)));
  // Specials may be selected using a separate, independently locked label.
  const special=safe.filter(r=>r.special?.approved===true&&
    beforeOff(r.special.lockedAt,r.closeAt)&&
    r.special.snapshotAt===r.forecast?.snapshotAt&&eligibleHighPayout(r));
  return {targetPerDay:1,selected,special,
    metTarget:selected.length+special.length>0,
    status:selected.length+special.length>0?"published":"qualified-race-not-available"};
}
