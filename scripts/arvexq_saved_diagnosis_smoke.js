const assert=require('node:assert/strict'),fs=require('node:fs');
const root={};new Function('window',fs.readFileSync('arvexq/ui/static/research/diagnosis_view.js','utf8'))(root);
const r={horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙',scratched:true}]};
const original={horses:[{horseNumber:1,mark:'◎',score:72.4,grade:'A',axes:{pure:.8}},
  {horseNumber:2,mark:'○',score:60,grade:'B'}]};
const p={rows:r.horses.map(h=>({horse:h,overallScoreExact:99,overallGrade:'S',predMark:'◎',overallReasons:['事後評価']}))};
const deps={original:()=>original,esc:String,started:()=>true,scratch:h=>!!h.scratched};
const before=JSON.stringify(original),html=root.ARVEXQDiagnosisView.render(r,p,deps);
assert.equal((html.match(/diagnosis-merged-row/g)||[]).length,2);
assert.ok(html.includes('72.4'));assert.ok(!html.includes('99.0'));
assert.ok(!html.includes('事後評価'));assert.ok(html.includes('取消'));
assert.equal(JSON.stringify(original),before);
const missing=root.ARVEXQDiagnosisView.render(r,p,{...deps,original:()=>null});
assert.ok(missing.includes('発走前の診断根拠は未保存'));
assert.ok(!missing.includes('99.0'));
console.log('ALL_RUNNER_DIAGNOSIS_PREOFF_ORIGINAL_POSTOFF_READONLY_PASS');

// Stage64 public products must be visible for every horse at every track,
// even after post; do not mislabel them as a verified pre-off lock.
for(const circuit of ['中央','地方']){
  const horses=Array.from({length:6},(_,i)=>({horseNumber:i+1,name:circuit+'馬'+(i+1)}));
  const values=Object.fromEntries(horses.map((h,i)=>[h.horseNumber,(i+1)/10]));
  const marks=['◎','○','▲','△','☆'].map((mark,i)=>({horseNumber:i+1,mark}));
  const r2={id:'race-'+circuit,date:'2026-10-24',circuit,predictionStatus:'ready',
    predictionModelVersion:'arvexq-stage64-product-v1',horses,predictionMarks:marks,
    prediction:{raceId:'race-'+circuit,date:'2026-10-24',circuit:circuit==='中央'?'jra':'nar',
      modelVersion:'arvexq-stage64-product-v1',productionEligible:true,predictionStatus:'ready',
      stages:{ability:{value:values},runningStyle:{value:Object.fromEntries(horses.map(h=>[h.horseNumber,[1,0,0,0]]))},
        probability:{calibrationVerified:false,value:{win:values,top3:values}}}}};
  const after=JSON.stringify(r2);
  const out=root.ARVEXQDiagnosisView.render(r2,{}, {...deps,original:()=>null});
  assert.equal((out.match(/diagnosis-merged-row/g)||[]).length,6);
  assert.ok(out.includes('能力指数')&&out.includes('推定1着率 10.0%')&&out.includes('推定3着内率 10.0%'));
  assert.ok(out.includes('確率は未校正')&&out.includes('公開Stage64'));
  assert.ok(out.includes('◎')&&out.includes('☆'));
  assert.ok(!out.includes('発走前の診断根拠は未保存')&&!out.includes('事後評価'));
  assert.equal(JSON.stringify(r2),after);
  const bad={...r2,prediction:{...r2.prediction,raceId:'wrong'}};
  const refused=root.ARVEXQDiagnosisView.render(bad,{}, {...deps,original:()=>null});
  assert.ok(refused.includes('発走前の診断根拠は未保存'));
}
console.log('JRA_NAR_STAGE64_ALL_RUNNER_DIAGNOSIS_VISIBLE_PASS');

// Stage64 absent ability never falls through into a legacy/post-result score.
const nullAbilityRace={id:'race-null',date:'2026-10-24',circuit:'中央',predictionStatus:'ready',
  predictionModelVersion:'arvexq-stage64-product-v1',horses:Array.from({length:5},(_,i)=>({horseNumber:i+1,name:'N'+i})),
  predictionMarks:['◎','○','▲','△','☆'].map((m,i)=>({horseNumber:i+1,mark:m})),
  prediction:{raceId:'race-null',date:'2026-10-24',circuit:'jra',modelVersion:'arvexq-stage64-product-v1',
    productionEligible:true,predictionStatus:'ready',stages:{ability:{value:{1:null,2:.2,3:.3,4:.4,5:.5}},
    probability:{value:{win:{1:.1},top3:{1:.3}},calibrationVerified:false}}}};
const nullHtml=root.ARVEXQDiagnosisView.render(nullAbilityRace,
  {rows:[{horse:nullAbilityRace.horses[0],overallScoreExact:99,overallGrade:'A'}]},
  {...deps,original:()=>null,started:()=>false});
assert.ok(!nullHtml.includes('99.0'));
console.log('STAGE64_NULL_SCORE_NO_LEGACY_LEAK_PASS');

// A distinct JRA/NAR API circuit is necessary; cross-circuit forecasts refuse.
const illegal={...nullAbilityRace,prediction:{...nullAbilityRace.prediction,circuit:'nar'}};
const illegalHtml=root.ARVEXQDiagnosisView.render(illegal,{}, {...deps,original:()=>null});
assert(!illegalHtml.includes('公開Stage64'),'never display cross-circuit Stage64 data');
console.log('JRA_NAR_API_CIRCUIT_MAPPING_AND_GUARD_PASS');
