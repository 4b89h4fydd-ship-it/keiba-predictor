// SMALL: immutable, pre-off trifecta receipts only. Never infer stakes or predictions.
import {usableForecast,validTicket} from "./contract.js";
export function summarize(races){
  const total={published:0,settled:0,hits:0,staked:0,returned:0,payable:0,selected:0};
  const history=[];
  for(const race of races||[]){
    if(!usableForecast(race))continue;
    total.published++;
    const result=race.result||{};
    if(result.status!=="confirmed"||!validTicket(result.trifecta))continue;
    total.settled++;
    const tickets=race.forecast.tickets.map(t=>typeof t==="string"?{combination:t}:t);
    const hit=tickets.some(t=>t.combination===result.trifecta);
    if(hit)total.hits++;
    const known=tickets.every(t=>Number.isFinite(t.stakeYen)&&t.stakeYen>0&&Number.isInteger(t.stakeYen)&&t.stakeYen%100===0)&&Number.isFinite(result.trifectaPayoutYen)&&result.trifectaPayoutYen>=0;
    if(known){
      const spent=tickets.reduce((s,t)=>s+t.stakeYen,0);
      const winnings=tickets.filter(t=>t.combination===result.trifecta).reduce((s,t)=>s+result.trifectaPayoutYen*t.stakeYen/100,0);
      total.staked+=spent;total.returned+=winnings;total.payable++;
    }
    history.push({id:race.id,venue:race.venue,raceNo:race.raceNo,hit,combination:result.trifecta,
      forecast: tickets.map(t=>t.combination),confirmedAt:result.confirmedAt||"",
      payoutVerified:known});
  }
  return {...total,hitRate:total.settled?total.hits/total.settled:null,
    roi:total.payable===total.settled&&total.staked>0?100*total.returned/total.staked:null,
    history};
}
