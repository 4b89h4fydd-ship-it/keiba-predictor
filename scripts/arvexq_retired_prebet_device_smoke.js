const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function loadStoredAiBet('),end=src.indexOf('function saveStoredAiBet(',start);
assert(start>=0&&end>start);
const loader=new Function('localStorage','aiBetStoreKey',src.slice(start,end)+'return loadStoredAiBet;');
const data=new Map([
 ['arvexq:prebet:v180:test',{items:[{kind:'馬連',combos:[[1,2]]}]}],
 ['arvexq:prebet:v300:test',{items:[{kind:'馬連',combos:[[3,4]]}]}]
]);
const localStorage={getItem:k=>JSON.stringify(data.get(k)||null)};
const load=loader(localStorage,id=>'arvexq:prebet:v300:'+id);
assert.deepEqual(load('test').items[0].combos,[[3,4]]);
data.delete('arvexq:prebet:v300:test');
assert.equal(load('test'),null,'retired receipts must not be loaded in the live UI');
assert(data.has('arvexq:prebet:v180:test'),'retired receipt remains for audit');
assert(!src.includes('loadStoredAiBet(r.id,true)'));
console.log('RETIRED_PREBET_DEVICE_LOOKUP_EXCLUDED_OK');
