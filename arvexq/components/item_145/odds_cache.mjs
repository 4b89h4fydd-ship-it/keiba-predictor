/* Cache ownership only; preserve exact TTLs, keys, fallback and no-store behavior. */
export async function cacheLookup(cache,key,force){
  const cached=await cache.match(key);
  return cached&&!force?cached:null;
}
export function cacheSave(cache,key,retainedKey,response,ctx){
  const retained=response.clone();retained.headers.set('Cache-Control','public, max-age=604800');
  ctx.waitUntil(Promise.all([cache.put(key,response.clone()),cache.put(retainedKey,retained)]));
}
export async function retainedLookup(cache,retainedKey){
  return retainedKey&&await cache.match(retainedKey);
}
