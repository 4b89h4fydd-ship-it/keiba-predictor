const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const js=fs.readFileSync(path.join(__dirname,'../arvexq/ui/static/research/race_identity.js'),'utf8');
const context={window:{},console};
vm.runInNewContext(js,context);
const module=context.window.ARVEXQRaceIdentity;
const rid='nar-2026-10-11-大井-08';
const race={id:rid,date:'2026-10-11',horses:[
  {horseNumber:1,name:'テストイチ'},
  {horseNumber:2,name:'テストニ'},
  {horseNumber:3,name:'テストサン'}
]};
module.remember(race);
function clean(r){return JSON.parse(JSON.stringify(module.sanitize(r)))}
const omittedNames=clean({...race,result:{
  status:'確定',finishers:[{horseNumber:1,finish:1},{horseNumber:2,finish:2,name:''},{horseNumber:3,finish:3,name:'テストサン'}],
  payouts:[{type:'馬連',combination:'1-2',amount:550}]
}});
assert.equal(omittedNames.result.status,'確定');
assert.deepEqual(omittedNames.result.finishers.map(h=>h.name),['テストイチ','テストニ','テストサン']);
assert.equal(omittedNames.result.payouts.length,1);
assert.equal(omittedNames._resultIdentityError,undefined);
const oneUnknown=clean({...race,result:{
  status:'確定',finishers:[{horseNumber:1,finish:1,name:'テストイチ'},
  {horseNumber:2,finish:2,name:'別の競走馬'}, {horseNumber:3,finish:3,name:'テストサン'}],
  payouts:[{type:'馬連',amount:100}]
}});
assert.equal(oneUnknown.result.status,'速報');
assert.deepEqual(oneUnknown.result.finishers.map(h=>h.horseNumber),[1,3]);
assert.equal(oneUnknown._resultIdentityRejectedCount,1);
assert.equal(oneUnknown.result.payouts,undefined);
const unknownHorse=clean({...race,result:{
  status:'確定',finishers:[{horseNumber:99,finish:1,name:''},{horseNumber:2,finish:2,name:''}]
}});
assert.equal(unknownHorse.result.finishers.length,1);
assert.equal(unknownHorse.result.finishers[0].name,'テストニ');
assert.equal(unknownHorse.result.status,'速報');
const absentResult=clean({...race});
assert.equal(absentResult.result,undefined);
console.log('RACE_RESULT_IDENTITY_OK');
