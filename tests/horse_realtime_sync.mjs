/* Verify race state progression independently of live race data. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import jsSupport from './stage4_js_support.cjs';
const source=fs.readFileSync('arvexq/ui/static/sports/unified-home.js','utf8');
const context={window:{},Date,Map,Set,String,Number,Math};
vm.runInNewContext(source,context,{filename:'unified-home.js'});
const home=context.window.ARVEXQUnifiedHome;
assert.equal(typeof home.liveModel,'function');
const day='2026-10-12',at=s=>new Date(day+'T'+s+':00+09:00');
const rows=[
 {id:'jra-'+day+'-東京-01',circuit:'中央',track:'東京',raceNumber:1,startTime:'10:00'},
 {id:'jra-'+day+'-東京-02',circuit:'中央',track:'東京',raceNumber:2,startTime:'10:40'},
 {id:'nar-'+day+'-浦和-01',circuit:'地方',track:'浦和',raceNumber:1,startTime:'10:10'},
 {id:'nar-'+day+'-浦和-02',circuit:'地方',track:'浦和',raceNumber:2,startTime:'10:50'},
 {id:'nar-'+day+'-浦和-03',circuit:'地方',track:'浦和',raceNumber:3,startTime:'11:10',result:{status:'中止'}}
];
const state=(clock,id)=>home.liveModel('horse',rows,day,at(clock)).find(r=>r.id.endsWith(id));
assert.equal(home.liveModel('horse',rows,day,at('09:59')).length,5);
assert.equal(state('09:59','東京-01').status,'soon');
assert.equal(state('09:59','東京-01').next,true);
assert.equal(state('10:01','東京-01').status,'running');
assert.equal(state('10:05','東京-01').status,'elapsed');
assert.equal(state('10:01','東京-02').next,true);
assert.equal(state('10:11','浦和-01').status,'running');
assert.equal(state('10:15','浦和-01').status,'elapsed');
// Time alone cannot mark a race as final. An official D1 published state
// must progress the card from 結果待ち to 速報, then 確定.
assert.equal(home.raceStatus('horse',{...rows[0],result:{status:'速報',
  finishers:[{horseNumber:4,finish:1}]}},day,at('10:06')),'flash');
assert.equal(home.labelFor('flash'),'速報');
const current=[
 {...rows[0],volatility:{morningPicks:{selected:true}},preRacePrediction:{frozen:true}},
 {...rows[1],result:{status:'確定',finishers:[{horseNumber:2,finish:1}]}}
];
const published=[
 {id:rows[0].id,raceStatus:'速報'},
 {id:rows[1].id,raceStatus:'速報'}
];
assert.equal(home.mergePublishedStatuses(current,published),1);
assert.equal(current[0].raceStatus,'速報');
assert.equal(current[0].preRacePrediction.frozen,true,'original sealed receipt survives');
assert.equal(current[0].volatility.morningPicks.selected,true,'selection survives status refresh');
assert.equal(current[1].result.status,'確定','official final never downgraded');
assert.equal(home.raceStatus('horse',current[0],day,at('10:06')),'flash');
assert.equal(home.mergePublishedStatuses(current,[{id:rows[0].id,raceStatus:'確定'}]),1);
assert.equal(home.raceStatus('horse',current[0],day,at('10:06')),'finished');
assert.equal(home.mergePublishedStatuses(current,[{id:rows[0].id,raceStatus:'速報'}]),0,
  'stale summary must not downgrade verified final');
assert.equal(home.mergePublishedStatuses(current,[{id:'irrelevant',raceStatus:'確定'}]),0);
const finishersOnly={...rows[2],result:{finishers:[{horseNumber:6,finish:1}]}};
assert.equal(home.raceStatus('horse',finishersOnly,day,at('10:16')),'flash',
  'published finishers cannot remain labelled waiting');
const lateOld={...rows[3]},newer={...rows[3],raceStatus:'確定'};
assert.equal(home.mergePublishedStatuses([lateOld],[newer]),1);
assert.equal(lateOld.raceStatus,'確定');
assert.equal(home.labelFor('running'),'進行中');
assert.equal(home.labelFor('soon'),'まもなく');
assert.equal(home.labelFor('elapsed'),'結果待ち');
assert.equal(home.raceStatus('horse',{...rows[0],raceStatus:'確定'},day,at('09:59')),'finished');
assert.equal(home.raceStatus('horse',{...rows[0],raceStatus:'進行中'},day,at('10:10')),'running');
assert.equal(state('10:11','浦和-02').next,true);
assert.equal(state('09:59','浦和-03').status,'cancelled');
assert.ok(home.liveModel('horse',rows,day,at('23:59')).some(r=>r.status==='elapsed'));
assert.notEqual(home.liveSignature('horse',rows,day,at('09:59')),
                home.liveSignature('horse',rows,day,at('10:01')));
assert.match(home.buttons('horse'),/data-home-page="selected"/);
assert.match(home.buttons('horse'),/data-home-page="special"/);
assert.match(home.buttons('horse'),/data-home-page="ai-stats"/);
assert.doesNotMatch(source,/kyotei|boat|競艇/i);
const ui=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert.match(ui,/ARVEXQHorsePortal\.home/);
assert.match(ui,/syncLiveUI\('horse'/);
assert.match(ui,/function refreshHomeOfficialStatuses\(\)/,
  'home must refetch verified official status instead of only repainting the clock');
assert.match(ui,/mergePublishedStatuses\(state\.races,rows\)/);
assert.match(ui,/homeOfficialStatusLastFetch<30000/);
assert.match(ui,/refreshHomeOfficialStatuses\(\);/);
assert.match(ui,/mergePublishedStatuses\(rows,state\.races\)/,
  'initial listing cannot downgrade server-confirmed races when fallback is stale');
const statusStart=ui.indexOf('function resultStatus('),
      statusEnd=ui.indexOf('function isFinal(',statusStart);
assert.ok(statusStart>=0&&statusEnd>statusStart,'production result-status authority exists');
const resultStatus=new Function(jsSupport.connectedFunctionSource(ui,'resultStatus')+'return resultStatus')();
assert.equal(resultStatus({raceStatus:'確定',result:{status:'速報'}}),'確定',
  'newer official D1 final supersedes cached preliminary detail');
assert.equal(resultStatus({raceStatus:'速報',result:{status:'確定'}}),'確定',
  'newer detail final never gets downgraded');
assert.equal(resultStatus({raceStatus:'速報',result:{status:''}}),'速報');
assert.equal(resultStatus({raceStatus:'',result:{status:''}}),'',
  'never invent a result from passage of time');
assert.match(ui,/10000/);
const styles=fs.readFileSync('arvexq/ui/static/sports/all-races.css','utf8');
assert.match(styles,/\.arv-all-race\.elapsed,\.arv-all-race\.finished/);
assert.match(styles,/opacity:\.63/);
const visual=fs.readFileSync('arvexq/ui/static/sports/unified-home.css','utf8');
for(const token of [
  'grid-template-columns:repeat(6,minmax(0,1fr))!important',
  '.arv-all-race[data-race-state="soon"]',
  '.arv-all-race[data-race-state="running"]',
  '.arv-all-race[data-race-state="elapsed"]',
  '.smart-race-row[data-race-state="running"]',
  '.arv-favorite-home-open[data-race-state="soon"]'
])assert.ok(visual.includes(token),'Missing shared horizontal race visual: '+token);
assert.ok(!visual.includes('grid-template-columns:repeat(3,minmax(0,1fr))!important'),
  'Old 3-column override must be removed');
assert.ok(visual.includes('height:49px!important'),'Race buttons must match compact reference height');
assert.ok(visual.includes('.smart-home .arv-all-venue{') &&
  visual.includes('background:transparent!important;border:0!important;box-shadow:none!important'),
  'Separate venue card borders must be removed');
assert.match(source,/button\.smart-race-row\[data-race-state\]/);
assert.match(source,/button\.arv-favorite-home-open\[data-race-state\]/);
console.log('HORSE_RACE_LIVE_JST_ADVANCE_OK');
