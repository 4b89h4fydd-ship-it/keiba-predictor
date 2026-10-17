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
test('a richer incoming source wins, different horse numbers never mix',()=>{
  const old=[{horseNumber:1,recentRaces:[{finish:4}]},{horseNumber:2,recentRaces:[{finish:6}]}];
  const next={horses:[{horseNumber:1,recentRaces:[{finish:1},{finish:2}]},{horseNumber:3,recentRaces:[]}]};
  const merged=mergeStoredHorseHistory(next,old);
  assert.deepEqual(merged.horses[0].recentRaces,[{finish:1},{finish:2}]);
  assert.equal(merged.horses[1].recentRaces.length,0);
});
test('empty or absent previous records are safe; incoming factual history survives',()=>{
  const input={horses:[{horseNumber:4,recentRaces:[{date:'2026-09-01'}]}]};
  assert.deepEqual(mergeStoredHorseHistory(input,[]),{horses:[{horseNumber:4,recentRaces:[{date:'2026-09-01'}]}]});
  assert.equal(needsHistoryPreservation({horses:[{horseNumber:4,recentRaces:[{date:'2026-09-01'}],allPastRuns:[{date:'2026-09-01'}]}]}),true);
});
test('worker is wired to a pre-overwrite DB read and history merge',async()=>{
  const {readFile}=await import('node:fs/promises');
  const source=await readFile(new URL('../worker.js',import.meta.url),'utf8');
  assert.match(source,/previousHorsesByRace/);
  assert.match(source,/mergeStoredHorseHistory\(payloadObject,savedHorses\)/);
  assert.match(source,/SELECT race_id,json_extract\(payload,'\$\.horses'\)/);
});
