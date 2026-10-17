'use strict';
// Updated production requirement: old win/place axes cannot revive.
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const race={horses:[{horseNumber:1,mark:'◎',honmeiRole:'win',podiumAxisEligible:true},{horseNumber:2,mark:'◎',honmeiRole:'axis'}],honmeiDecision:{horseNumber:1,axisHorseNumber:2}};
for(const circuit of ['中央','地方'])for(const raceStatus of ['発走前','発走済','確定']){
 assertNoForecast({...race,circuit,raceStatus});
}
console.log('old win/place axes cannot revive OK');
