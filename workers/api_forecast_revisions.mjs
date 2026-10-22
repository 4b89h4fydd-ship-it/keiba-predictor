// Versioned forecasts live beside original D1 snapshots. Original tables are read-only here.
const TABLE_SQL=[
 `CREATE TABLE IF NOT EXISTS forecast_revisions (race_id TEXT NOT NULL,revision_id TEXT NOT NULL,race_date TEXT NOT NULL,model_version TEXT NOT NULL,created_at TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(race_id,revision_id))`,
 `CREATE TABLE IF NOT EXISTS forecast_revision_current (race_id TEXT PRIMARY KEY,revision_id TEXT NOT NULL,updated_at TEXT NOT NULL)`
];
const headers={'content-type':'application/json; charset=utf-8','cache-control':'no-store','access-control-allow-origin':'*','access-control-allow-headers':'content-type,authorization,x-sync-token'};
const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers});
const STORAGE='arvexq-storage-gzip-v1';
const utf8=new TextEncoder();
const sha=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
export async function restoreStoredJSON(stored){
 const value=JSON.parse(stored);
 if(value?.storageEncoding!==STORAGE)return stored;
 if(!Number.isInteger(value.bytes)||value.bytes<=0||value.bytes>1000000)throw Error('invalid storage length');
 const bytes=Uint8Array.from(atob(value.gzipBase64),x=>x.charCodeAt(0));
 const reader=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
 const chunks=[];let size=0;
 while(true){const {done,value:chunk}=await reader.read();if(done)break;size+=chunk.length;
  if(size>value.bytes){await reader.cancel();throw Error('storage expansion limit')};chunks.push(chunk)}
 const raw=new Uint8Array(size);let offset=0;for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.length}
 if(size!==value.bytes||await sha(raw)!==value.sha256)throw Error('storage checksum mismatch');
 return new TextDecoder('utf-8',{fatal:true}).decode(raw);
}
export async function compressStoredJSON(raw){
 const bytes=utf8.encode(raw),compressed=new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer());
 let binary='';for(let i=0;i<compressed.length;i+=8192)binary+=String.fromCharCode(...compressed.subarray(i,i+8192));
 const stored=JSON.stringify({storageEncoding:STORAGE,bytes:bytes.length,sha256:await sha(bytes),gzipBase64:btoa(binary)});
 return utf8.encode(stored).length<bytes.length?stored:raw;
}
function authorized(request,env){const token=String(env.SYNC_TOKEN||'');return token.length>0&&(
 request.headers.get('x-sync-token')===token||request.headers.get('authorization')==='Bearer '+token);}
export async function forecastRevisions(request,env){
 const url=new URL(request.url),path=url.pathname;
 if(request.method==='OPTIONS')return new Response('',{headers});
 if(path==='/api/admin/forecast-revisions/migrate'){
  if(request.method!=='POST')return response({ok:false,error:'method not allowed'},405);
  if(!authorized(request,env))return response({ok:false,error:'unauthorized'},401);
  await env.DB.batch(TABLE_SQL.map(sql=>env.DB.prepare(sql)));
  return response({ok:true,version:'arvexq-forecast-revision-v1',original_tables_modified:false});
 }
 if(path.startsWith('/api/forecast-revisions/')){
  if(request.method!=='GET')return response({ok:false,error:'method not allowed'},405);
  const id=decodeURIComponent(path.slice('/api/forecast-revisions/'.length));
  try{
   const current=await env.DB.prepare(`SELECT r.payload_json FROM forecast_revisions r JOIN forecast_revision_current c ON c.race_id=r.race_id AND c.revision_id=r.revision_id WHERE r.race_id=?`).bind(id).first();
   if(!current)return response({ok:true,raceId:id,storageEncoding:STORAGE,currentForecastRevisionId:null,forecastRevisions:[]});
   const rows=await env.DB.prepare('SELECT payload_json FROM forecast_revisions WHERE race_id=? ORDER BY created_at,revision_id').bind(id).all();
   const selected=JSON.parse(await restoreStoredJSON(current.payload_json));
   const restored=await Promise.all((rows.results||[]).map(r=>restoreStoredJSON(r.payload_json)));
   // Keep raw numeric spellings used by Python's immutable revision checksum.
   return new Response('{"ok":true,"storageEncoding":'+JSON.stringify(STORAGE)+',"raceId":'+JSON.stringify(id)+',"currentForecastRevisionId":'+JSON.stringify(selected.revisionId)+',"forecastRevisions":['+restored.join(',')+']}',{headers});
  }catch(error){
   if(/no such table.*forecast_revision/.test(String(error)))return response({ok:true,raceId:id,storageEncoding:STORAGE,schemaReady:false,currentForecastRevisionId:null,forecastRevisions:[]});
   throw error;
  }
 }
 if(path==='/api/admin/forecast-revisions'){
  if(request.method!=='POST')return response({ok:false,error:'method not allowed'},405);
  if(!authorized(request,env))return response({ok:false,error:'unauthorized'},401);
  const body=await request.json(),raw=body.revisionRawJson;
  if(typeof raw!=='string'||new TextEncoder().encode(raw).length>1000000)return response({ok:false,error:'invalid revision size'},400);
  let revision;try{revision=JSON.parse(raw)}catch{return response({ok:false,error:'invalid revision JSON'},400)}
  const {raceId,revisionId,raceDate,modelVersion,createdAt}=revision||{};
  if(revision.version!=='arvexq-forecast-revision-v1'||!raceId||!/^\d{4}-\d{2}-\d{2}$/.test(raceDate||'')||
     !/^[a-f0-9]{64}$/.test(revisionId||'')||typeof modelVersion!=='string'||!Number.isFinite(Date.parse(createdAt||''))||
     !['retrospective','preoff-candidate'].includes(revision.analysisType)||!Array.isArray(revision.horses))
    return response({ok:false,error:'invalid revision identity'},400);
  const seen=new Set();let honmei=0;
  for(const horse of revision.horses){
   if(!Number.isInteger(horse.horseNumber)||horse.horseNumber<=0||seen.has(horse.horseNumber)||
      !['','◎','○','▲','△','☆','注'].includes(horse.mark))return response({ok:false,error:'invalid horse marks'},400);
   const p=horse.probabilities||{},keys=['win','top2','top3'];
   if(keys.some(k=>p[k]!==undefined&&(!Number.isFinite(p[k])||p[k]<0||p[k]>1))||
      (keys.every(k=>p[k]!==undefined)&&(p.win>p.top2+1e-9||p.top2>p.top3+1e-9)))
     return response({ok:false,error:'invalid horse probabilities'},400);
   seen.add(horse.horseNumber);if(horse.mark==='◎')honmei++;
  }
  if(honmei>1)return response({ok:false,error:'multiple honmei'},400);
  if((revision.betPlan?.items||[]).reduce((n,item)=>n+(item.combos||[]).length,0)>10)
    return response({ok:false,error:'ticket limit exceeded'},400);
  const source=await env.DB.prepare('SELECT race_date FROM race_details WHERE race_id=?').bind(raceId).first();
  if(!source||source.race_date!==raceDate)return response({ok:false,error:'source race mismatch'},409);
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw)))).map(x=>x.toString(16).padStart(2,'0')).join('');
  if(body.payloadSha256!==digest)return response({ok:false,error:'revision checksum mismatch'},400);
  let stored;
  if(body.revisionStorageJson!==undefined){
   try{if(typeof body.revisionStorageJson!=='string'||utf8.encode(body.revisionStorageJson).length>utf8.encode(raw).length||await restoreStoredJSON(body.revisionStorageJson)!==raw)throw Error('storage mismatch');stored=body.revisionStorageJson}
   catch{return response({ok:false,error:'invalid compressed revision'},400)}
  }else stored=await compressStoredJSON(raw);
  const previous=await env.DB.prepare('SELECT payload_sha256 FROM forecast_revisions WHERE race_id=? AND revision_id=?').bind(raceId,revisionId).first();
  if(previous&&previous.payload_sha256!==digest)return response({ok:false,error:'immutable revision conflict'},409);
  await env.DB.batch([
   env.DB.prepare('INSERT INTO forecast_revisions(race_id,revision_id,race_date,model_version,created_at,payload_json,payload_sha256) VALUES(?,?,?,?,?,?,?) ON CONFLICT(race_id,revision_id) DO NOTHING').bind(raceId,revisionId,raceDate,modelVersion,createdAt,stored,digest),
   env.DB.prepare('INSERT INTO forecast_revision_current(race_id,revision_id,updated_at) VALUES(?,?,?) ON CONFLICT(race_id) DO UPDATE SET revision_id=excluded.revision_id,updated_at=excluded.updated_at').bind(raceId,revisionId,new Date().toISOString())
  ]);
  return response({ok:true,raceId,revisionId,original_tables_modified:false});
 }
 return response({ok:false,error:'not found'},404);
}
