/* Verify race state progression independently of live race data. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
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
assert.equal(home.labelFor('running'),'進行中');
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
assert.match(ui,/10000/);
const styles=fs.readFileSync('arvexq/ui/static/sports/all-races.css','utf8');
assert.match(styles,/\.arv-all-race\.elapsed,\.arv-all-race\.finished/);
assert.match(styles,/opacity:\.63/);
console.log('HORSE_RACE_LIVE_JST_ADVANCE_OK');
