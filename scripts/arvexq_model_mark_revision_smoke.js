'use strict';
// Updated production requirement: old model approvals do not authorize a new production engine.
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const race={id:'nar-old',horses:[{horseNumber:1}],modelMarkRevisions:[{approvalId:'user-approved-past-five-from-2026-10-09-20-10-jst',horses:[{horseNumber:1,mark:'◎'}]}],officialMarkRevisions:[{horses:[{horseNumber:1,mark:'◎'}]}]};
for(const circuit of ['中央','地方'])for(const raceStatus of ['発走前','発走済','確定']){
 assertNoForecast({...race,circuit,raceStatus});
}
console.log('old model approvals do not authorize a new production engine OK');
