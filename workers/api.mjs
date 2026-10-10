// The exported production source is preserved byte-for-byte in its own module.
import original from './api_preserved.mjs';
import {storageAudit} from './api_storage_audit.mjs';
import {snapshotExport} from './api_snapshot_export.mjs';
export default {fetch(request,env,ctx){
  if(new URL(request.url).pathname==='/api/admin/snapshot-export')return snapshotExport(request,env);
  if(new URL(request.url).pathname==='/api/admin/storage-audit'){
    if(request.method!=='GET')return Response.json({ok:false,error:'method not allowed'},{status:405});
    return storageAudit(request,env);
  }
  return original.fetch(request,env,ctx);
}};
