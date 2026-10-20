// Offline connection contracts plus differential existing Worker/UI behavior.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {gunzipSync, gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root = process.cwd();
const doc = root + '/docs/independence/route-connection-stage3-20261021/';
const records = JSON.parse(gunzipSync(fs.readFileSync(doc+'connections.json.gz')));
const ac = {exports:{},module:{exports:{}}};ac.module.exports=ac.exports;
vm.runInNewContext(process.binding('natives')['internal/deps/acorn/acorn/dist/acorn'],ac);
const acorn=ac.exports;
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const ast=acorn.parse(source,{ecmaVersion:'latest'});
const nodes=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type==='FunctionDeclaration')nodes.push(n);for(const v of Object.values(n))if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v)}walk(ast);
const helpers=[...new Set(records.filter(r=>r.kind==='existing-ui-function-forward').map(r=>r.box_target))].map(p=>fs.readFileSync(p,'utf8')).join('\n');
let uiContracts=0;
for(const r of records.filter(r=>r.kind==='existing-ui-function-forward')){
 const name=r.caller.symbol, publicNode=nodes.find(n=>n.id.name===name), privateNode=nodes.find(n=>n.id.name===r.original_private_name);
 assert.ok(publicNode&&privateNode);
 const ctx=vm.createContext({});
 vm.runInContext(helpers+'\n'+source.slice(privateNode.start,privateNode.end)+'\n'+source.slice(publicNode.start,publicNode.end),ctx);
 assert.equal(ctx[name].length,publicNode.params.length);
 const receiver={sentinel:'receiver'},payload={missing:null,horses:[{circuit:'地方'}]},answer={data:payload};let calls=0;
 ctx[r.original_private_name]=function(...args){calls++;assert.equal(this,receiver);assert.equal(args[0],payload);assert.equal(args[1],undefined);assert.equal(args[2],payload);return answer};
 assert.equal(await ctx[name].call(receiver,payload,undefined,payload),answer);assert.equal(calls,1);
 const error=Error('original failure');ctx[r.original_private_name]=()=>{throw error};
 await assert.rejects(async()=>ctx[name].call(receiver,payload),e=>e===error);uiContracts++;
}
let esmAliases=0;
for(const r of records.filter(r=>r.kind==='esm-object-reexport')){
 const [box,original]=await Promise.all([import(pathToFileURL(root+'/'+r.box_target)),import(pathToFileURL(root+'/'+r.original_source))]);
 assert.equal(box[r.caller.imported],original[r.caller.imported]);esmAliases++;
}
for(const r of records.filter(r=>r.kind==='existing-worker-fetch-forward')){
 const box=await import(pathToFileURL(root+'/'+r.box_target));let count=0;
 const req={},env={},ctx={},out={};const worker={fetch(a,b,c){count++;assert.equal(this,worker);assert.equal(a,req);assert.equal(b,env);assert.equal(c,ctx);return out}};
 assert.equal(box.fetchExisting(worker,req,env,ctx),out);assert.equal(count,1);
}
// Execute real existing UI functions with fixtures, rather than replacing their implementation.
function uiContext(text,routeHelpers){
 const tree=acorn.parse(text,{ecmaVersion:'latest'});const iife=tree.body.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='CallExpression'&&n.expression.callee.type==='FunctionExpression').expression.callee.body.body;
 const declarations=iife.filter(n=>n.type==='FunctionDeclaration'||n.type==='VariableDeclaration'&&n.declarations.every(d=>['CENTRAL','LOCAL','COURSE','ARVEXQ_RACE_CACHE_SCHEMA'].includes(d.id.name)));
 const ctx=vm.createContext({window:{},state:{races:[],favoriteRaces:{}},localStorage:{getItem:()=>null,setItem:()=>{}},console});
 vm.runInContext(routeHelpers+'\n'+declarations.map(n=>text.slice(n.start,n.end)).join('\n'),ctx);return ctx;
}
let uiDifferentials=0,workerDifferentials=0;
const baseline=process.argv[2];
if(baseline){
 const before=uiContext(fs.readFileSync(baseline+'/arvexq/ui/static/app.js','utf8'),'');const after=uiContext(source,helpers);
 const race={id:'nar-2026-10-18-大井-01',circuit:'地方',track:'大井',raceNumber:1,horses:[{horseNumber:1,winOdds:2.5}],result:{status:'確定',finishers:[{horseNumber:1,finish:1}]}};
 const cases=[['winOddsText',[2.5]],['winOddsText',[null]],['oddsText',[2.5]],['oddsClass',[null]],['horseByNo',[race,1]],['horseByNo',[race,9]],['resultStatus',[race]],['isFinal',[race]],['isFlash',[race]],['hasAnyResultData',[race]],['hasResultData',[race]],['resultFinish',[race,1]],['actualCornerCount',[race]],['actualCornerLabel',[1]],['raceIsGraded',[race]],['kochiFinalRace',[[race]]],['cacheKey',['2026-10-18']],['detailCacheKey',[race.id]],['canGoBack',[]]];
 for(const [name,args] of cases){
  const a=JSON.stringify(before[name](...structuredClone(args))),b=JSON.stringify(after[name](...structuredClone(args)));assert.equal(b,a,name);uiDifferentials++;
 }
 globalThis.fetch=async()=>{throw Error('Stage4: external fetch forbidden')};
 const detail={id:race.id,date:'2026-10-18',circuit:'地方',horses:[{horseNumber:1,allPastRuns:[{track:'東京',finish:2},{track:'大井',finish:1}],missing:null}],preRacePrediction:{frozen:true,marks:['◎']}};
 const raw=Buffer.from(JSON.stringify(detail));const envelope={arvexqFullPayload:{version:'arvexq-full-payload-v1',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex'),gzipBase64:gzipSync(raw).toString('base64')}};
 function environment(mode){const calls=[];return {calls,env:{ASSETS:{fetch:async req=>new Response('original static asset',{status:200})},DB:{prepare(sql){calls.push([sql]);return {bind(...args){calls[calls.length-1].push(args);return this},async first(){if(mode==='error')throw Error('database unavailable');if(sql.includes('json_extract')&&sql.includes('race_details')&&mode==='packed')return {payload:JSON.stringify(envelope),analysis_ready:1,updated_at:123};return null},async all(){return {results:[]}},async run(){return {success:true,meta:{changes:0}}}}}}}}}
 for(const file of ['api.mjs','web.mjs']){
  const beforeWorker=(await import(pathToFileURL(baseline+'/workers/'+file))).default;const afterWorker=(await import(pathToFileURL(root+'/workers/'+file))).default;
  const cases=file==='api.mjs'?[['/api/race/'+encodeURIComponent(race.id),'packed'],['/api/race/'+encodeURIComponent(race.id),'error'],['/api/race/nar-2026-10-18-帯広-01','none'],['/api/forecast-revisions/test','none'],['/api/admin/storage-audit','none'],['/api/admin/storage-environment','none']]:[['/','none'],['/api/live-odds/invalid','none'],['/api/live-odds/'+encodeURIComponent(race.id),'none']];
  for(const [path,mode] of cases){const a=environment(mode),b=environment(mode);const req=new Request('https://offline.invalid'+path),ctx={waitUntil(){}};
   const x=await beforeWorker.fetch(req.clone(),a.env,ctx),y=await afterWorker.fetch(req.clone(),b.env,ctx);
   assert.equal(y.status,x.status,path);const body=await y.text();assert.equal(body,await x.text(),path);assert.deepEqual([...y.headers],[...x.headers]);assert.deepEqual(b.calls,a.calls,'DB calls must not double');
   if(mode==='packed'){assert.deepEqual(JSON.parse(body).detail,detail);assert.equal(b.calls.length,3)}workerDifferentials++;
  }
 }
}
console.log(JSON.stringify({uiContracts,esmAliases,workerForwardContracts:2,uiDifferentials,workerDifferentials,baseline:baseline||null}));
