'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const crypto=require('node:crypto');
const {readAppSource}=require('../arvexq/ui/app_source.cjs');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
function prediction(source,race){
 const fixed=Date.parse('2026-10-10T00:00:00Z');
 class FixedDate extends Date{constructor(...args){super(...(args.length?args:[fixed]))}static now(){return fixed}}
 const saved=new Map(),store={getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,String(v)),removeItem:k=>saved.delete(k)};
 const document={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
 const window={document,addEventListener:()=>{},innerWidth:390,location:{href:'https://arvexq.test/'},navigator:{standalone:false},localStorage:store};
 const context={window,document,localStorage:store,sessionStorage:store,console,Date:FixedDate,
  URL,URLSearchParams,Math,JSON,Intl,Number,String,Array,Object,Set,Map,Promise,RegExp,
  parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,navigator:window.navigator,
  location:window.location,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
 vm.createContext(context);
 assert.ok(source.includes(boot));
 vm.runInContext(source.replace(boot,'window.audit={predict,state};'),context,{timeout:15000});
 window.audit.state.date=race.date;window.audit.state.circuit=race.circuit;
 window.audit.state.races=[race];
 const p=window.audit.predict(JSON.parse(JSON.stringify(race)));
 return JSON.parse(JSON.stringify({rows:p.rows.map(x=>{const y={...x};delete y.horse;return y}),
   scenarios:p.scenarios.map(x=>({code:x.code,prob:x.prob})),
   stages:p.plan&&p.plan.stages,outcome:Object.fromEntries(Object.entries(p.outcome||{}).map(([k,v])=>[k,
    Array.isArray(v)?v.map(z=>z&&z.horse?z.horse.horseNumber:z):v&&v.horse?v.horse.horseNumber:v])),profile:p.profile}));
}
function run(){
 const assembled=readAppSource();
 if(process.env.ARVEXQ_PYTHON_SOURCE){
  const python=fs.readFileSync(process.env.ARVEXQ_PYTHON_SOURCE,'utf8');
  assert.equal(assembled,python,'browser, static build and Node tools must use identical source order');
 }
 const manifest=JSON.parse(fs.readFileSync('docs/refactor/extracted-js-functions.json','utf8'));
 for(const row of manifest){
  const source=fs.readFileSync(row.after,'utf8'),at=source.indexOf('function '+row.name+'(');
  assert.ok(at>=0,row.name);
  const original=source.slice(at,at+row.characters);
  assert.equal(crypto.createHash('sha256').update(original).digest('hex'),row.source_sha256,row.name+' formula changed');
 }
 const golden=JSON.parse(fs.readFileSync('tests/fixtures/js-prediction-main-c025fea.json','utf8'));
 for(const row of golden.cases)assert.deepEqual(prediction(assembled,row.race),row.expected,row.race.title);
 console.log('DOMAIN_JS_EXTRACTION_PASS 31 formulas / source parity / central-local-debut-jump predictions');
}
module.exports={prediction};
if(require.main===module)run();
