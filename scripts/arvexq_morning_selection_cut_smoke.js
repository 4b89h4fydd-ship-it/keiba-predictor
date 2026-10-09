'use strict';
// Synthetic regressions only. Morning picks are not calibrated hit rates.
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('arvexq/ui/static/morning/selection_cut.js','utf8');
const w={};new Function('window',source)(w);
const n=(v)=>Number(v)||0,chronological=(a,b)=>a.race.startTime.localeCompare(b.race.startTime);
const rows=[
 {race:{id:'JRA-01',raceNumber:5,startTime:'13:10'},selection:{selected:true,score:70}},
 {race:{id:'NAR-02',raceNumber:10,startTime:'18:10'},selection:{selected:true,score:66}},
 {race:{id:'NAR-01',raceNumber:2,startTime:'10:00'},selection:{selected:true,score:72}},
 {race:{id:'NOT-QUALIFIED',raceNumber:1,startTime:'09:50'},selection:{selected:false,score:98}},
];
const x=w.ARVEXQMorningSelection.allStrictQualifiers(rows,{n,chronological});
assert.deepEqual(x.map(z=>z.race.id),['NAR-01','JRA-01','NAR-02'],'all eligible races kept, no max-one cap');
assert.equal(w.ARVEXQMorningSelection.version,'strict-unlimited-morning-v1');
console.log('MORNING_SELECTION_UNLIMITED_OK '+x.length);
