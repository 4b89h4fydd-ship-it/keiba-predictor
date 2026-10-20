// The exported production source is preserved byte-for-byte in its own module.
import original from '../../../workers/api_preserved.mjs';
import {storageAudit} from '../../../workers/api_storage_audit.mjs';
import {snapshotExport} from '../../../workers/api_snapshot_export.mjs';
import {readCompressedRace,storageEnvironment,compressStoredSnapshot} from '../../../workers/api_full_snapshot.mjs';
import {enhanceNarGoingResponse} from '../../../workers/nar_going_moisture.mjs';
import {readV3Facts} from '../../../workers/api_v3_facts.mjs';
export default {async fetch(request,env,ctx){
  const url=new URL(request.url);
  // Retired candidate transport: never read, migrate or publish model revisions.
  // Existing D1 rows remain available to the authenticated snapshot backup.
  if(url.pathname.startsWith('/api/forecast-revisions/')||url.pathname.startsWith('/api/admin/forecast-revisions')){
    return Response.json({ok:false,error:'forecast revision route retired'},{status:410,headers:{'access-control-allow-origin':'*','cache-control':'no-store'}});
  }
  if(url.pathname==='/api/admin/snapshot-compress')return compressStoredSnapshot(request,env);
  // Explicit saved-only v3 view on the SAME canonical race route.
  // The normal display, compressed legacy delivery and sync paths are untouched.
  if(request.method==='GET'&&url.pathname.startsWith('/api/race/')&&url.searchParams.get('view')==='v3-facts'){
    return readV3Facts(request,async id=>{
      const restored=await readCompressedRace(env,id);
      if(restored)return restored;
      const displayUrl=new URL(request.url);
      displayUrl.searchParams.set('view','display');
      return original.fetch(new Request(displayUrl,request),storageEnvironment(env,false),ctx);
    });
  }
  if(request.method==='GET'&&url.pathname.startsWith('/api/race/')){
      try{const id=decodeURIComponent(url.pathname.slice('/api/race/'.length));const restored=await readCompressedRace(env,id);if(restored)return enhanceNarGoingResponse(restored,fetch,id)}
    catch(e){return Response.json({ok:false,error:'saved detail restore unavailable'},{status:503,headers:{'access-control-allow-origin':'*'}})}
  }
  if(new URL(request.url).pathname==='/api/admin/snapshot-export')return snapshotExport(request,env);
  if(new URL(request.url).pathname==='/api/admin/storage-audit'){
    if(request.method!=='GET')return Response.json({ok:false,error:'method not allowed'},{status:405});
    return storageAudit(request,env);
  }
  return original.fetch(request,storageEnvironment(env,url.pathname==='/api/day'&&url.searchParams.get('details')!=='0'),ctx);
}};
