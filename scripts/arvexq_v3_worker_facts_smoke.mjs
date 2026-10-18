import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import worker from '../workers/api.mjs';
import {factualProjection} from '../workers/api_v3_facts.mjs';

function race(circuit='jra') {
  const venue=circuit==='jra'?'京都':'高知';
  return {id:circuit+'-2026-10-18-'+venue+'-03',
    date:'2026-10-18',circuit:circuit==='jra'?'中央':'地方',
    track:venue,startTime:'12:00',fieldSize:2,
    horses:[
      {horseNumber:2,name:'保存二',winOdds:3.4,
        allPastRuns:[{date:'2026-10-01',finish:3,mark:'◎',preRaceBet:{hidden:1}}],
        recentRaces:[{date:'2026-10-18',finish:1},{date:'2026-10-20',finish:1}],
        mark:'◎',preRaceBet:{buy:'secret'},modelProbabilities:[0.8]},
      {horseNumber:1,name:'保存一',placeOdds:'1.2-1.5',popularity:0,
        recentRaces:[{date:'2026-10-03',finish:2}]}
    ],
    result:{finishers:[{horseNumber:2,finish:1}],payouts:[{kind:'単勝',payout:120}]},
    preRacePrediction:{winner:2},preRaceBet:{tickets:[1]},predictionMarks:['◎']
  };
}
function mockDB(data,{compressed=false,missing=false}={}) {
  const dbReads=[], writes=[];
  let payload=JSON.stringify(data);
  if(compressed) {
    const raw=Buffer.from(payload);
    const zipped=gzipSync(raw);
    payload=JSON.stringify({arvexqFullPayload:{
      version:'arvexq-full-payload-v1',bytes:raw.length,
      sha256:createHash('sha256').update(raw).digest('hex'),
      gzipBase64:zipped.toString('base64')
    }});
  }
  return {dbReads,writes,
    prepare(sql) {
      dbReads.push(sql);
      if (/\b(?:INSERT|UPDATE|DELETE)\b/i.test(sql)) writes.push(sql);
      return {bind(...args) {
        return {
          async first(){
            if(missing)return null;
            if(sql.includes("AS codec"))return {codec:compressed?'arvexq-full-payload-v1':null};
            if(sql.includes('SELECT payload,analysis_ready,updated_at'))return {payload,analysis_ready:0,updated_at:1};
            if(sql.includes('json_remove(payload'))return {payload,analysis_ready:0,updated_at:1};
            if(sql.includes('FROM race_summaries'))return {race_id:data.id};
            throw Error('unexpected D1 query: '+sql.slice(0,140));
          },
          async all(){return {results:[]}}
        };
      }};
    }
  };
}
async function optin(raceData,compressed=false) {
  const direct=factualProjection(raceData,raceData.id);
  assert.equal(direct.coverage.completeness.history.runnersWithPriorRuns,2);
  const db=mockDB(raceData,{compressed});
  const req=new Request('https://test.invalid/api/race/'+encodeURIComponent(raceData.id)+'?view=v3-facts');
  const res=await worker.fetch(req,{DB:db},null);
  assert.equal(res.status,200,'Worker v3 must serve '+raceData.id+'; body='+await res.clone().text());
  const body=await res.json();
  assert.equal(body.race_id,raceData.id);
  assert.equal(body.detail.schema,'arvexq-v3-factual-screen-1');
  assert.deepEqual(body.detail.rows.map(r=>r.horseNumber),[1,2]);
  assert.equal(body.detail.rows[1].observedPriorRunCount,1);
  assert.equal(body.detail.rows[1].readiness.history,'partial-unverified');
  assert.equal(body.detail.rows[1].readiness.win,'observed');
  assert.equal(body.detail.rows[1].readiness.place,'missing');
  assert.equal(body.detail.rows[1].readiness.odds,'incomplete');
  assert.equal(body.detail.rows[0].readiness.history,'partial-unverified');
  assert.equal(body.detail.rows[0].readiness.win,'missing');
  assert.equal(body.detail.rows[0].readiness.popularity,'invalid');
  assert.equal(body.detail.rows[0].readiness.canClaimFullyRetrieved,false);
  assert.equal(body.detail.rows[1].recentRaces[0].date,'2026-10-01');
  assert.equal(body.detail.results,null);
  assert.equal(body.detail.resultFields,null);
  assert.equal(body.detail.marks,null);
  assert.equal(body.detail.tickets,null);
  assert.equal(body.detail.predictionStatus,'not-implemented');
  assert.equal(body.detail.coverage.careerCompleteness,'unverified');
  assert.equal(body.detail.coverage.completeness.roster.state,'unverified');
  assert.equal(body.detail.coverage.completeness.roster.officialVerified,false);
  assert.equal(body.detail.coverage.completeness.history.state,'partial-unverified');
  assert.equal(body.detail.coverage.completeness.history.allCareerRunsVerified,false);
  assert.equal(body.detail.coverage.completeness.odds.state,'incomplete');
  assert.equal(body.detail.coverage.completeness.odds.marketFreshnessVerified,false);
  assert.equal(body.detail.displayReadiness.complete,false);
  assert.equal(body.detail.displayReadiness.canClaimFullyRetrieved,false);
  assert.equal(body.detail.displayReadiness.roster,'unverified');
  assert.equal(body.detail.displayReadiness.history,'partial-unverified');
  assert.equal(body.detail.displayReadiness.odds,'incomplete');
  assert.equal(body.detail.quoteFields.quoteFreshness,'unknown');
  assert.equal(body.detail.oddsFields.win.find(x=>x.horseNumber===2)?.value,3.4);
  assert.equal(body.detail.oddsFields.popularity.find(x=>x.horseNumber===1)?.state,'invalid');
  assert.equal(body.detail.oddsFields.popularity.find(x=>x.horseNumber===1)?.value,null);
  assert.equal(res.headers.get('cache-control'),'no-store');
  const clean=JSON.stringify(body);
  for(const forbidden of ['modelProbabilities','preRaceBet','preRacePrediction','predictionMarks','"mark"','"payouts"'])
    assert.ok(!clean.includes(forbidden),'forbidden output: '+forbidden);
  assert.equal(db.writes.length,0,'read-only worker');
  return db.dbReads;
}
for(const c of ['jra','nar']) {
  const sample=race(c);
  assert.ok((await optin(sample,false)).length>0);
  assert.ok((await optin(sample,true)).length>0);
  // Explicitly refuse a circuit-mislabeled snapshot.
  const wrong={...sample,circuit:c==='jra'?'NAR':'JRA'};
  assert.throws(()=>factualProjection(wrong,wrong.id),/identity\/circuit/);
  // Never join two horses with same number, no guess about identity.
  const duplicate=structuredClone(sample);
  duplicate.horses[1].horseNumber=2;
  assert.throws(()=>factualProjection(duplicate,duplicate.id),/ambiguous/);
  const heavy=race(c);
  heavy.horses[0].allPastRuns=Array.from({length:8},(_,i)=>({
    date:'2026-10-'+String(i+1).padStart(2,'0'),finish:3
  }));
  heavy.horses[0].recentRaces=[{date:'2026-10-08',track:'test'},
    {date:'2026-10-18',finish:2}];
  const measured=factualProjection(heavy,heavy.id);
  assert.equal(measured.rows.find(x=>x.horseNumber===2).observedPriorRunCount,9);
  assert.equal(measured.rows.find(x=>x.horseNumber===2).recentRaces.length,5);
  assert.equal(measured.rows.find(x=>x.horseNumber===2).readiness.observedPriorRunCount,9);
  assert.equal(measured.coverage.observedPriorRuns,10);
}
const original=race();
const db=mockDB(original,{missing:true});
const req=new Request('https://test.invalid/api/race/'+encodeURIComponent(original.id)+'?view=v3-facts');
const missing=await worker.fetch(req,{DB:db},null);
assert.equal(missing.status,404);
assert.deepEqual(db.writes,[]);
const invalid=await worker.fetch(new Request('https://test.invalid/api/race/not-a-race?view=v3-facts'),{DB:db},null);
assert.equal(invalid.status,422);
console.log('ARVEXQ_V3_D1_WORKER_READONLY_PASS saved/compact JRA+NAR, 404, identity, no results/marks/bets, no write');
