const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function independentSpecialEvidence(');
const end=src.indexOf('/* Only live observed prediction authority',start);
assert(start>=0&&end>start,'independent ☆/注 authority must exist');
const n=(v,d=0)=>v==null?d:(Number.isFinite(Number(v))?Number(v):d);
function historicalWindow(h,r){
 return (h.recentRaces||[]).filter(v=>String(v.date)<String(r.date))
    .sort((a,b)=>b.date.localeCompare(a.date)).slice(0,5);
}
const alloc=new Function('observedHistory','n','isNarRace','verifiedJraMargin',src.slice(start,end)+
  'return assignIndependentSpecialMarks')(historicalWindow,n,()=>true,()=>true);
const race={date:'2026-10-15',track:'園田',distance:1400,surface:'ダート'};
const ordered=Array.from({length:7},(_,idx)=>{
 const no=idx+1;
 const runs=Array.from({length:4},(_,i)=>{
  const front=no<=3?1:7;
  return {date:'2026-10-'+String(10-i).padStart(2,'0'),finish:Math.min(9,no+i),
    fieldSize:12,cornerPositions:[front,front,front],
    marginSeconds:1.5,opponentLevel:.45,
    track:'園田',surface:'ダート',distance:1400};
 });
 if(no===5)runs.forEach((z,i)=>{z.finish=i===1?2:4+i%2;z.cornerPositions=[8,8,7]});
 if(no===6)runs.forEach((z,i)=>{
  z.finish=i===0?6:i===1?3:5;z.cornerPositions=[6,6,6];
  z.opponentLevel=.82;z.marginSeconds=.3;
 });
 return {horse:{horseNumber:no,recentRaces:runs},threeFactorScore:1-idx*.07};
});
const e=alloc(ordered,race);
assert.deepEqual(ordered.map(z=>e[z.horse.horseNumber].mark),
 ['◎','○','▲','△','☆','注',''],'☆ and 注 should be selected by observed facts');
assert(e[5].closingGainRuns>0&&e[6].noteReasons.length>=2);
const noHistory=structuredClone(ordered);
noHistory.forEach(z=>z.horse.recentRaces=[]);
assert.deepEqual(noHistory.map(z=>alloc(noHistory,race)[z.horse.horseNumber].mark),
 ['◎','○','▲','△','','',''],'missing evidence is not an automatic special mark');
ordered[3].horse.recentRaces=structuredClone(ordered[4].horse.recentRaces);
const moved=alloc(ordered,race);
assert.equal(moved[4].mark,'☆');
assert.equal(moved[5].mark,'△');
assert.equal(moved[6].mark,'注');
assert(src.includes('var independent=assignIndependentSpecialMarks(valid,r);'),'NAR uses special authority');
assert(src.includes('function assignObservedPredictionMarks('),'both circuits share special mark allocation');
assert(!src.includes('function eligibleOptionalStar('),'old star allocator was physically removed');
const bet=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
assert(bet.includes('<i>注</i>'),'bet guide explains the independent 注 lane');
console.log('INDEPENDENT_STAR_NOTE_PYTHON_BROWSER_ROLE_POLICY_OK');
