const assert=require('node:assert/strict'),fs=require('node:fs');
const root={};new Function('window',fs.readFileSync('arvexq/ui/static/research/race_identity.js','utf8'))(root);
const card={id:'race1',date:'2026-10-10',horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'}]};
root.ARVEXQRaceIdentity.remember(card);
const contaminated={...card,fieldSize:3,horses:[{horseNumber:1,name:'甲',winOdds:2.1},
  {horseNumber:2,name:'別レースの馬',winOdds:1.1},{horseNumber:3,name:'別の出走馬'}],
  result:{finishers:[{horseNumber:1,name:'他場の勝馬',finish:1}]},preRacePrediction:{keep:true}};
const bytes=JSON.stringify(contaminated),safe=root.ARVEXQRaceIdentity.sanitize(contaminated);
assert.equal(safe.horses.length,2);assert.equal(safe.fieldSize,2);
assert.equal(safe.horses[0].winOdds,2.1);assert.equal(safe.horses[1].name,'乙');
assert.equal(safe.horses[1].winOdds,undefined,'never transfer wrong horse odds');
assert.equal(safe.result,undefined);assert.equal(safe._resultIdentityError,true);
assert.deepEqual(safe.preRacePrediction,{keep:true});assert.equal(JSON.stringify(contaminated),bytes,'do not change stored raw original');
const genuine={...card,result:{finishers:[{horseNumber:1,name:'甲',finish:1}]}};
assert.deepEqual(root.ARVEXQRaceIdentity.sanitize(genuine).result,genuine.result);
assert.deepEqual(root.ARVEXQRaceIdentity.sanitize({...contaminated,date:'2026-10-11'}).horses,contaminated.horses,'different date must not use this roster');
console.log('RACE_IDENTITY_NO_GHOST_RUNNER_NO_WRONG_RESULT_NO_RAW_MUTATION_PASS');
