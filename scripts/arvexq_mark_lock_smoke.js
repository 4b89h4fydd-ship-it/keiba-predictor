'use strict';
// Updated production requirement: no device or server lock restores live marks.
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const race={id:'race',horses:[{horseNumber:1},{horseNumber:2,scratched:true,mark:'◎'}],preRacePrediction:{frozen:true,horses:[{horseNumber:1,mark:'◎'}]},preRaceBet:{items:[{amount:1000}]}};
for(const circuit of ['中央','地方'])for(const raceStatus of ['発走前','発走済','確定']){
 assertNoForecast({...race,circuit,raceStatus});
}
console.log('no device or server lock restores live marks OK');
