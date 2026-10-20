'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('arvexq/components/shared_ui/0193_fetchEdgeRace.js','utf8');
async function check(fail){
 const original={id:'race-1',date:'2026-10-20',horses:[{horseNumber:1,name:'原本'}],preRacePrediction:{fixedAt:'original'}};
 const before=JSON.stringify(original),calls=[],state={races:[],date:original.date},status={},saved=[];
 const sandbox={state,instantTrackDetails:{},loadDetailCache:()=>null,detailState:()=>status,
 updateDetailSections(){},edgeRaceUrl:id=>'https://api.test/api/race/'+id+'?view=display',traceRaceDetail(){},
 edgeFetchJson:async url=>{calls.push(url);if(fail)throw Error('http 404');return {ok:true,detail:original}},
 normalizeDetailSummary:(row,id)=>row||{id},mergeRaceReflection:(a,b)=>Object.assign({},a,b),
 entryDataAvailable:r=>!!(r&&r.horses&&r.horses.length),saveDetailCache:(id,r)=>saved.push(r),setTimeout};
 vm.runInNewContext(source,sandbox);
 const result=await sandbox.fetchEdgeRace(original.id,true,1);
 assert.equal(calls.length,1);assert.equal(calls[0],'https://api.test/api/race/race-1?view=display');
 assert.equal(JSON.stringify(original),before,'frozen original must stay unchanged');
 if(fail){assert.equal(result,null);assert.equal(saved.length,0);assert.match(status.error,/404/)}
 else {assert.equal(result.horses[0].name,'原本');assert.equal(result.preRacePrediction.fixedAt,'original');assert.equal(saved.length,1);assert.equal(status.error,'')}
 assert.equal(status.busy,false);
}
(async()=>{await check(false);await check(true);console.log('CANONICAL_RACE_READER_NO_CANDIDATE_FANOUT_PASS')})().catch(e=>{console.error(e);process.exit(1)});
