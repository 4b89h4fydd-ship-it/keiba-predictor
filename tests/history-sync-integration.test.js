import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker.js';

function makeDB(priorPayload, failRead=false) {
  const db={writes:[],prepare(sql){
    return {bind(...params){
      return {sql,params,async all(){
        if(sql.includes("SELECT race_id,json_extract(payload,'$.horses')")) {
          if(failRead)throw Error('prior history unavailable');
          return {results:[{race_id:params[0],horses:JSON.stringify(priorPayload.horses)}]};
        }
        return {results:[]};
      },async first(){return null}};
    }};
  },async batch(statements){
    db.writes.push(...statements);
    return statements.map(()=>({success:true}));
  }};
  return db;
}
async function sync(db,details){
  const request=new Request('https://api.test/api/sync',{
    method:'POST',
    headers:{'content-type':'application/json','x-sync-token':'test-key'},
    body:JSON.stringify({details})
  });
  return worker.fetch(request,{DB:db,SYNC_TOKEN:'test-key'});
}
test('D1 sync reads and preserves previous history even when new source has shorter nonempty arrays',async()=>{
  const old={id:'nar-2026-10-07-大井-11',horses:[{horseNumber:1,
    recentRaces:[{date:'2026-09-20'},{date:'2026-09-10'},{date:'2026-09-01'}],
    allPastRuns:[{date:'2026-09-20'},{date:'2026-09-10'},{date:'2026-09-01'}]}]};
  const incoming={id:old.id,date:'2026-10-07',horses:[{horseNumber:1,status:'出走取消',
    recentRaces:[{date:'2026-09-20'}],allPastRuns:[{date:'2026-09-20'}]}]};
  const db=makeDB(old);
  const response=await sync(db,[incoming]);
  assert.equal(response.status,200,await response.clone().text());
  const wrote=db.writes.find(x=>x.sql.includes('INSERT INTO race_details'));
  assert.ok(wrote,'race detail must be persisted');
  const saved=JSON.parse(wrote.params[2]);
  assert.equal(saved.horses[0].recentRaces.length,3);
  assert.equal(saved.horses[0].allPastRuns.length,3);
  assert.equal(saved.horses[0].status,'出走取消');
});
test('failed protection query blocks destructive sync writes',async()=>{
  const old={horses:[{horseNumber:1,recentRaces:[{date:'2026-09-20'}]}]};
  const incoming={id:'nar-2026-10-07-大井-11',date:'2026-10-07',
    horses:[{horseNumber:1,recentRaces:[]}]};
  const db=makeDB(old,true);
  const response=await sync(db,[incoming]);
  assert.equal(response.status,500);
  assert.equal(db.writes.length,0);
});
