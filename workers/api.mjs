import {fetchExisting as _arvexq_fetch_existing} from '../arvexq/components/item_173/api_entry.mjs';
// The exported production source is preserved byte-for-byte in its own module.
import original from './api_preserved.mjs';
import {forecastRevisions} from '../arvexq/components/item_148/api_forecast_revisions.mjs';
import {storageAudit} from '../arvexq/components/item_171/api_storage_audit.mjs';
import {snapshotExport} from '../arvexq/components/item_148/api_snapshot_export.mjs';
import {readCompressedRace,compressStoredSnapshot} from '../arvexq/components/item_139/api_full_snapshot.mjs';
import {storageEnvironment} from '../arvexq/components/item_174/api_full_snapshot.mjs';
const _arvexq_existing_worker = {async fetch(request,env,ctx){
  const url=new URL(request.url);
  // Retire Banei from live traffic without touching archived D1 rows.
  if(request.method==='GET'&&(/^\/api\/(?:race|odds)\//).test(url.pathname)){
    let id;try{id=decodeURIComponent(url.pathname.replace(/^\/api\/(?:race|odds)\//,''))}catch{return Response.json({ok:false,error:'invalid race id'},{status:400})}
    if(/^nar-\d{4}-\d{2}-\d{2}-(?:帯広|帯広ば)-\d{2}$/.test(id))return Response.json({ok:false,error:'race venue excluded'},{status:404});
  }
  if(url.pathname.startsWith('/api/forecast-revisions/')||url.pathname.startsWith('/api/admin/forecast-revisions'))return forecastRevisions(request,env);
  if(url.pathname==='/api/admin/snapshot-compress')return compressStoredSnapshot(request,env);
  if(request.method==='GET'&&url.pathname.startsWith('/api/race/')){
      try{const restored=await readCompressedRace(env,decodeURIComponent(url.pathname.slice('/api/race/'.length)));if(restored)return restored}
    catch(e){return Response.json({ok:false,error:'saved detail restore unavailable'},{status:503,headers:{'access-control-allow-origin':'*'}})}
  }
  if(url.pathname==='/api/admin/snapshot-export')return snapshotExport(request,env);
  if(url.pathname==='/api/admin/storage-audit'){
    if(request.method!=='GET')return Response.json({ok:false,error:'method not allowed'},{status:405});
    return storageAudit(request,env);
  }
  return original.fetch(request,storageEnvironment(env,url.pathname==='/api/day'&&url.searchParams.get('details')!=='0'),ctx);
}};

export default {async fetch(request, env, ctx) {
  return _arvexq_fetch_existing(_arvexq_existing_worker, request, env, ctx);
}};
