"""Execute existing recovery functions with a failed optional detail decorator."""
import subprocess
from pathlib import Path


def test_recovery_keeps_validated_rows_and_never_invents_marks():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["node", "-e", r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const ctx={
 n:Number,esc:String,racecardMarkLegend:()=>'',traceRaceDetail:()=>{},
 runnerStyleSection:()=>{throw Error('optional decoration unavailable')},
 morningSavedMarkRows:r=>r.horses.map(h=>({horse:h,predMark:''})),
 racecardEntryRow:(r,h,row)=>ctx.ARVEXQProductionMarks.visible(row)
};
ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/marks.js','utf8'),ctx);
vm.runInContext(source.slice(source.indexOf('function minimalRacecardPanel('),
 source.indexOf('var racePredictionTasks=')),ctx);
const race={id:'synthetic',horses:[{horseNumber:1},{horseNumber:2}]};
const prediction={rows:[{horse:race.horses[0],predMark:'◎',serverPreoffMark:true},
 {horse:race.horses[1],predMark:'○',serverPreoffMark:true}]};
const before=JSON.stringify({race,prediction});
assert(ctx.safeEntryPanel(race,prediction).includes('◎○'));
assert(!ctx.safeEntryPanel(race,{rows:[{horse:race.horses[0],predMark:'◎'}]}).includes('◎'));
assert(!ctx.minimalRacecardPanel(race).includes('◎'));
assert.equal(JSON.stringify({race,prediction}),before);
"""], cwd=root, check=True, capture_output=True, text=True)
