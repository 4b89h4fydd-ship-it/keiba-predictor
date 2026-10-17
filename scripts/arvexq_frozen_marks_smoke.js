'use strict';
// Updated production requirement: old immutable originals remain archival across start and final states.
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const race={id:'race',horses:[{horseNumber:1}],preRacePrediction:{frozen:true,horses:[{horseNumber:1,mark:'◎'}]},morningMarkSnapshot:{horses:[{horseNumber:1,mark:'◎'}]}};
for(const circuit of ['中央','地方'])for(const raceStatus of ['発走前','発走済','確定']){
 assertNoForecast({...race,circuit,raceStatus});
}
console.log('old immutable originals remain archival across start and final states OK');
