const fs=require('fs'),vm=require('vm');
// Replay the current browser engine from supplied, dated factual race inputs.
// Historical originals are read only; this command makes no network or storage writes.
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const root=fs.readFileSync(process.env.ARVEXQ_REPLAY_SOURCE||'arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
const saved=new Map(),storage={getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,String(v)),removeItem:k=>saved.delete(k)};
const doc={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,location:{href:'https://audit.invalid/'},navigator:{standalone:false},localStorage:storage,document:doc};
const ctx={window,document:doc,localStorage:storage,sessionStorage:storage,console,URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,navigator:window.navigator,location:window.location,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
for(const f of ['morning/ticket_lane_classifier.js','betting/bet_view.js'])vm.runInContext(fs.readFileSync('arvexq/ui/static/'+f,'utf8'),ctx);
vm.runInContext(root.replace(boot,'window.audit={predict,buildAiBetPlan,narScoreRows,analysisRace};'),ctx);
let output=[];
for(const race of input){
 const prediction=window.audit.predict(race),plan=window.audit.buildAiBetPlan(race,prediction);
 output.push({id:race.id,rows:prediction.rows.map(z=>({no:z.horse.horseNumber,score:z.narScore,mark:z.predMark,rates:z.historicalRates,factors:z.narEvidence,p1:z.p1Probability})),plan});
}
console.log(JSON.stringify(output));
