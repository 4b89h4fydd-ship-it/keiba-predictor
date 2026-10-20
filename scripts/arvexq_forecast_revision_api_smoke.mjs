import assert from 'node:assert/strict';
import api from '../workers/api.mjs';
// Exercise the real production router. Even authenticated requests must not
// create schemas, read retired candidates or change their current pointer.
let queries=0;
const DB={prepare(){queries++;throw Error('retired route accessed D1')},batch(){queries++;throw Error('retired route wrote D1')}};
for(const path of ['/api/forecast-revisions/test','/api/admin/forecast-revisions','/api/admin/forecast-revisions/migrate']){
 for(const method of ['GET','POST','OPTIONS']){
  const response=await api.fetch(new Request('https://api.test'+path,{method,headers:{'x-sync-token':'test-only-token'}}),{DB,SYNC_TOKEN:'test-only-token'},{});
  assert.equal(response.status,410,method+' '+path);
  assert.equal((await response.json()).ok,false);
 }
}
assert.equal(queries,0,'retirement must preserve all existing D1 records');
console.log('RETIRED_FORECAST_TRANSPORT_NO_D1_READ_OR_WRITE_PASS');
