function suitability(rows,sc,pressure){var out={};pressure=pressure||pressureInfo(rows);var i,x,win,place,show,j,q,scenarioScores=[],frontFadePenalty,baseWin,basePlace,baseShow;for(i=0;i<rows.length;i++){x=rows[i];win=place=show=0;scenarioScores=[];frontFadePenalty=x.goProb>=.50?Math.max(0,x.fade-.38)*x.goProb:0;for(j=0;j<sc.length;j++){q=scenarioSuit(x,sc[j].code,pressure);scenarioScores.push({code:sc[j].code,score:q});baseWin=q*.72+x.ability*.20+x.hold*.08-frontFadePenalty*.18;basePlace=q*.57+x.ability*.20+(1-x.fade)*.13+x.flexibility*.06+x.hold*.04-frontFadePenalty*.065;baseShow=q*.46+x.ability*.20+(1-x.fade)*.14+x.move*.09+x.flexibility*.06+x.hold*.05-frontFadePenalty*.030;if(x.goProb>=.52&&x.fade<=.25){baseWin+=.025;basePlace+=.018;baseShow+=.012}if(sc[j].code==='C'&&x.collapseBeneficiary>.60){basePlace+=.035;baseShow+=.025}win+=sc[j].prob*baseWin;place+=sc[j].prob*basePlace;show+=sc[j].prob*baseShow}win=clamp(win,0,1.25);place=clamp(place,0,1.25);show=clamp(show,0,1.25);var overall=win*.54+place*.29+show*.17;out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:overall,rankScore:win*.62+place*.24+show*.14,scenario:scenarioScores}}return out}















