const KEY='arvexqFullPayload',VERSION='arvexq-full-payload-v1';
export async function restoreBytes(envelope){
  const ref=envelope&&envelope[KEY];
  if(!ref||ref.version!==VERSION||!(ref.bytes>0&&ref.bytes<=100000000))throw Error('invalid full snapshot envelope');
  const zipped=Uint8Array.from(atob(ref.gzipBase64),c=>c.charCodeAt(0));
  const raw=await new Response(new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');
  if(raw.byteLength!==ref.bytes||hash!==ref.sha256)throw Error('full snapshot restore mismatch');
  return new Uint8Array(raw);
}
export async function readCompressedRace(env,id){
  const exists=await env.DB.prepare(`SELECT CASE WHEN json_valid(payload) THEN json_extract(payload,'$.arvexqFullPayload.version') ELSE NULL END AS codec FROM race_details WHERE race_id=?`).bind(id).first();
  if(!exists||exists.codec!==VERSION)return null;
  const record=await env.DB.prepare('SELECT payload,analysis_ready,updated_at FROM race_details WHERE race_id=?').bind(id).first();
  const envelope=JSON.parse(record.payload),raw=await restoreBytes(envelope);
  const summary=await env.DB.prepare('SELECT * FROM race_summaries WHERE race_id=?').bind(id).first();
  const odds=await env.DB.prepare('SELECT horse_no,win_odds,popularity,body_weight,body_weight_change,horse_status,updated_at FROM odds_current WHERE race_id=? ORDER BY horse_no').bind(id).all();
  const prefix=JSON.stringify({ok:true,race_id:id,summary:summary||null,analysis_ready:!!record.analysis_ready,
    detail_updated_at:record.updated_at,odds:odds.results||[]}).slice(0,-1)+',"detail":';
  const encode=new TextEncoder();
  const stream=new ReadableStream({start(controller){controller.enqueue(encode.encode(prefix));controller.enqueue(raw);controller.enqueue(encode.encode('}'));controller.close()}});
  return new Response(stream,{headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store',
    'access-control-allow-origin':'*','access-control-allow-headers':'content-type,authorization,cache-control,pragma,x-sync-token'}});
}
export function rewriteDetailSQL(sql,compactDay=false){
  if(compactDay&&/FROM\s+race_details\s+WHERE\s+race_date\s*=/.test(sql))
    return sql.replace(/\bpayload\b/,"CASE WHEN json_valid(payload) THEN json_remove(payload,'$.arvexqFullPayload','$.massFeatureArchive','$.massFeatureSnapshot') ELSE payload END AS payload");
  if(/INSERT\s+INTO\s+race_details\s*\(/i.test(sql)&&/ON CONFLICT\(race_id\)/i.test(sql)&&!/\bWHERE\b/i.test(sql))
    return sql.trim().replace(/;$/,'')+' WHERE race_details.payload IS NOT excluded.payload OR race_details.analysis_ready IS NOT excluded.analysis_ready OR race_details.race_date IS NOT excluded.race_date';
  return sql;
}
export function storageEnvironment(env,compactDay=false){
  const db=env.DB;
  return {...env,DB:new Proxy(db,{get(target,key){if(key==='prepare')return sql=>db.prepare(rewriteDetailSQL(sql,compactDay));const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value}})};
}
export async function compressStoredSnapshot(request,env){
  if(!env.SYNC_TOKEN||request.headers.get('authorization')!=='Bearer '+env.SYNC_TOKEN)
    return Response.json({ok:false,error:'unauthorized'},{status:401});
  if(request.method!=='POST')return Response.json({ok:false,error:'method not allowed'},{status:405});
  let body;try{body=await request.json()}catch{return Response.json({ok:false,error:'invalid JSON'},{status:400})}
  const id=String(body.race_id||'');
  if(!id||!/^[a-f0-9]{64}$/.test(body.expected_sha256||'')||!body.payload)
    return Response.json({ok:false,error:'invalid backup proof'},{status:400});
  const row=await env.DB.prepare(`SELECT payload,CASE WHEN json_valid(payload) THEN json_extract(payload,'$.arvexqFullPayload.version') ELSE NULL END AS codec FROM race_details WHERE race_id=?`).bind(id).first();
  if(!row)return Response.json({ok:false,error:'missing original'},{status:404});
  if(row.codec===VERSION)return Response.json({ok:true,already_compressed:true});
  const old=new TextEncoder().encode(row.payload);
  const oldHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',old)),x=>x.toString(16).padStart(2,'0')).join('');
  if(oldHash!==body.expected_sha256)return Response.json({ok:false,error:'original changed since backup'},{status:409});
  let raw;try{raw=await restoreBytes(body.payload)}catch{return Response.json({ok:false,error:'compression restore failed'},{status:400})}
  if(body.payload[KEY].sha256!==oldHash||raw.byteLength!==old.byteLength)
    return Response.json({ok:false,error:'compression does not restore original'},{status:400});
  // Build the index on the server from the verified original, never trust submitted marks.
  const original=JSON.parse(new TextDecoder().decode(raw)),thin={};
  const keep=new Set(['preRacePrediction','preRaceBet','preRaceBetPlan','morningTicketEvidence','morningPicks','environmentMeta','volatility','preparedMeta','result','modelRevisions','authorizedRevisions','massFeatureArchive','dataReadiness']);
  for(const [key,value] of Object.entries(original))if(key!==KEY&&(keep.has(key)||value===null||typeof value!=='object'))thin[key]=value;
  if(Array.isArray(original.horses))thin.horses=original.horses.filter(h=>h&&typeof h==='object').map(h=>Object.fromEntries(Object.entries(h).filter(([key,value])=>key==='careerTransport'||value===null||typeof value!=='object')));
  thin[KEY]=body.payload[KEY];
  const packed=JSON.stringify(thin);
  if(new TextEncoder().encode(packed).byteLength>=old.byteLength)return Response.json({ok:true,skipped_no_saving:true});
  const result=await env.DB.prepare('UPDATE race_details SET payload=? WHERE race_id=? AND payload=?').bind(packed,id,row.payload).run();
  if(!result.meta||result.meta.changes!==1)return Response.json({ok:false,error:'concurrent original update'},{status:409});
  return Response.json({ok:true,restored_sha256:oldHash,original_bytes:old.byteLength,stored_bytes:new TextEncoder().encode(packed).byteLength,meta:result.meta});
}
