"""Run the actual JS adapter; fixtures are synthetic, not performance evidence."""
import subprocess
from pathlib import Path


def test_unified_receipt_uses_complete_active_roster():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["node", "-e", r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={};ctx.window=ctx;vm.createContext(ctx);
for(const name of ['prediction','marks'])
 vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/'+name+'.js','utf8'),ctx);
function fixture(){
 const horses=[1,2,3,4,5].map(n=>({horseNumber:n,name:'horse'+n}));
 return {id:'nar-2099-01-01-test-01',date:'2099-01-01',circuit:'地方',startTime:'12:00',horses,
 unifiedForecast:{version:'arvexq-unified-live-v1',raceId:'nar-2099-01-01-test-01',
 raceDate:'2099-01-01',circuit:'地方',researchOnly:true,probabilitiesCalibrated:false,
 roster:horses.map(h=>({...h})),marks:['◎','○','▲','△','☆'].map((markSymbol,i)=>({horseNumber:i+1,markSymbol})),
 receiptSha256:'a'.repeat(64),modelHash:'b'.repeat(64),trainedThrough:'2098-12-31',
 capturedAt:'2098-12-31T09:00:00+09:00',modelVersion:'synthetic',pace:{text:'test'}}};
}
function check(r,ok){
 const before=JSON.stringify(r),p=ctx.ARVEXQProductionPrediction.build(r);
 assert.equal(ctx.ARVEXQProductionPrediction.current().source==='arvexq-unified-preoff',ok);
 assert.equal(JSON.stringify(r),before);
 if(ok){
 assert.equal(p.rows.filter(x=>ctx.ARVEXQProductionMarks.visible(x)==='◎').length,1);
 assert.equal(ctx.ARVEXQProductionMarks.visible(p.rows.find(x=>x.horse.horseNumber===6)),'');
 }
}
for(const status of ['取消','出走取消','競走取消','除外','競走除外','欠場']){
 const r=fixture();r.horses.push({horseNumber:6,name:'withdrawn',status});check(r,true);
}
for(const flag of ['scratched','withdrawn']){
 const r=fixture();r.horses.push({horseNumber:6,name:'withdrawn',[flag]:true});check(r,true);
}
check(fixture(),true);
let r=fixture();r.horses.pop();check(r,false);
r=fixture();r.horses.push({...r.horses[0]});check(r,false);
r=fixture();r.horses[0].name='different';check(r,false);
r=fixture();r.horses.push({horseNumber:6,name:'active'});check(r,false);
r=fixture();r.horses[0].scratched=true;check(r,false);
r=fixture();r.horses[0].horseNumber=0;check(r,false);
"""], cwd=root, check=True, capture_output=True, text=True)
