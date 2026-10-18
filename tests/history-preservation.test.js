import test from 'node:test';
import assert from 'node:assert/strict';
import {needsHistoryPreservation,mergeStoredHorseHistory} from '../history-preservation.js';

test('compact odds and racecard sync cannot erase verified historical runs', ()=>{
  const stored=[{horseNumber:1,recentRaces:[{date:'2026-10-01',finish:1},{date:'2026-09-01',finish:3}],allPastRuns:[{date:'2026-10-01',finish:1},{date:'2026-09-01',finish:3}]}];
  const incoming={id:'nar-2026-10-07-大井-11',horses:[{horseNumber:1,name:'A',winOdds:3,recentRaces:[],allPastRuns:[],status:'出走取消'}]};
  const before=JSON.stringify(stored),raw=JSON.stringify(incoming);
  assert.equal(needsHistoryPreservation(incoming),true);
  const result=mergeStoredHorseHistory(incoming,stored);
  assert.equal(result.horses[0].recentRaces.length,2);
  assert.equal(result.horses[0].allPastRuns.length,2);
  assert.equal(result.horses[0].status,'出走取消');
  assert.equal(result.horses[0].winOdds,3);
  assert.equal(JSON.stringify(stored),before);
  assert.equal(JSON.stringify(incoming),raw);
  assert.notStrictEqual(result.horses[0].recentRaces,stored[0].recentRaces);
});
test('equal-count replacement unions dates and preserves stored values on conflict',()=>{
  const old=[{horseNumber:1,allPastRuns:[{date:'2026-10-01',finish:2},{date:'2026-09-01',finish:3}]}];
  const next={horses:[{horseNumber:1,allPastRuns:[{date:'2026-10-01',finish:8,track:'東京'},{date:'2026-08-01',finish:4}]}]};
  const merged=mergeStoredHorseHistory(next,old).horses[0].allPastRuns;
  assert.deepEqual(merged.map(x=>x.date),['2026-10-01','2026-09-01','2026-08-01']);
  assert.equal(merged[0].finish,2);
  assert.equal(merged[0].track,'東京');
});
test('richer incoming records are added while distinct historical records remain',()=>{
  const old=[{horseNumber:1,recentRaces:[{finish:4}]}];
  const next={horses:[{horseNumber:1,recentRaces:[{finish:1},{finish:2}]}]};
  const merged=mergeStoredHorseHistory(next,old);
  assert.deepEqual(merged.horses[0].recentRaces,[{finish:4},{finish:1},{finish:2}]);
});
test('previous archive survives absent or unproven equal-sized replacement',()=>{
  const archive={sha256:'old',storedRunCount:8,payload:'verified'};
  const old=[{horseNumber:1,careerArchive:archive,allPastRuns:[{date:'2026-01-01'}]}];
  const absent=mergeStoredHorseHistory({horses:[{horseNumber:1,allPastRuns:[]}]},old);
  assert.deepEqual(absent.horses[0].careerArchive,archive);
  const equal=mergeStoredHorseHistory({horses:[{horseNumber:1,careerArchive:{sha256:'changed',storedRunCount:8},allPastRuns:[]}]},old);
  assert.deepEqual(equal.horses[0].careerArchive,archive);
  const richer={sha256:'richer',storedRunCount:9,payload:'richer'};
  const expanded=mergeStoredHorseHistory({horses:[{horseNumber:1,careerArchive:richer,allPastRuns:[]}]},old);
  assert.deepEqual(expanded.horses[0].careerArchive,richer);
});
test('empty or absent previous records are safe; incoming factual history survives', ()=>{
  const input={horses:[{horseNumber:4,recentRaces:[{date:'2026-09-01'}],allPastRuns:[{date:'2026-09-01'}]}]};
  assert.deepEqual(mergeStoredHorseHistory(input,[]),input);
  assert.equal(needsHistoryPreservation({horses:[{horseNumber:4,recentRaces:[{date:'2026-09-01'}],allPastRuns:[{date:'2026-09-01'}]}]}),true);
});
test('worker is wired to a pre-overwrite DB read and history merge',async()=>{
  const {readFile}=await import('node:fs/promises');
  const source=await readFile(new URL('../worker.js',import.meta.url),'utf8');
  assert.match(source,/previousHorsesByRace/);
  assert.match(source,/mergeStoredHorseHistory\(payloadObject,savedHorses\)/);
  assert.match(source,/SELECT race_id,json_extract\(payload,'\$\.horses'\)/);
});
