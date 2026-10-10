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
