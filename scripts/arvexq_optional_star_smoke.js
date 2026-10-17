'use strict';
// Updated production requirement: independent special marks are disabled.
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const race={horses:[{horseNumber:1,mark:'☆',integratedEvaluation:{mark:'☆',coreAbilityScore:99}},{horseNumber:2,mark:'注'}]};
for(const circuit of ['中央','地方'])for(const raceStatus of ['発走前','発走済','確定']){
 assertNoForecast({...race,circuit,raceStatus});
}
console.log('independent special marks are disabled OK');
