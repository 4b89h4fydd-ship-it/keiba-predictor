#!/usr/bin/env node
const fs=require('node:fs');
const assert=require('node:assert/strict');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function applyFrozenMarks(r,p){');
const end=src.indexOf('\n}',start)+2;
assert.ok(start>=0&&end>start, 'frozen marks entrypoint missing');
const original=src.slice(start,end);
assert.doesNotMatch(original, /\block&&lock\.reason\b/, 'unbound lock regression');
const frozen={version:'arvexq-official-mark-revision-v1',
  reason:'公式馬場変更', fixedAt:'2026-10-10T10:00:00+09:00',
  horses:[{horseNumber:1,mark:'◎',singleWinSuitable:true,lockedEvaluation:{score:90,grade:'S'}},
          {horseNumber:2,mark:'○'}]};
const n=(v,otherwise=0)=>Number(v)||otherwise;
const fn=new Function('raceMarkClock','authorizedPreOffMarks','loadFrozenMarks',
  'isScratchHorse','n','validMorningMarkSnapshot','markFreezeKey','localStorage',
  original+';return applyFrozenMarks')(
    ()=>({valid:true,started:false,remaining:12}),
    ()=>frozen,()=>null,(horse)=>!!horse.scratched,n,()=>false,()=>'',{
      setItem(){assert.fail('server marks must not be replaced by local edits')}
    });
const race={id:'jra-2026-10-10-京都-05',date:'2026-10-10',
  horses:[{horseNumber:1},{horseNumber:2}]};
const pred={rows:[{horse:race.horses[0],predMark:'△',overallScore:66},
                  {horse:race.horses[1],predMark:'▲',overallScore:65}]};
const result=fn(race,pred);
assert.equal(result.markFreeze.source,'official-course-revision');
assert.equal(result.markFreeze.reason,'公式馬場変更');
assert.equal(result.markFreeze.fixedAt,'2026-10-10T10:00:00+09:00');
assert.deepEqual(result.rows.map(x=>x.predMark),['◎','○']);
assert.equal(result.rows[0].overallScore,90);
assert.equal(result.rows[0].singleWinSuitable,true);
assert.equal(result.rows[0].markFrozen,true);
console.log('FROZEN_MARKS_VALID_PRODUCTION_CODE_PASS');
