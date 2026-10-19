import {sourceOdds} from '../../../workers/live_odds.mjs';
import {savedOdds} from '../../../workers/saved_odds.mjs';
import {cacheLookup,cacheSave,retainedLookup} from '../item_145/odds_cache.mjs';
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    // Retired boat-racing paths must not be served by the SPA fallback.
    if(/^\/(?:kyotei(?:\/|$)|sports\/boat(?:-app|-data|\.html)(?:\/|$))/.test(url.pathname))
      return new Response('Not Found',{status:404,headers:{'Cache-Control':'no-store'}});
    if(!url.pathname.startsWith('/api/live-odds/'))return env.ASSETS.fetch(request);
    if(request.method!=='GET')return new Response('Method not allowed',{status:405});
    let source,date,retainedKey;
    try{
      const id=decodeURIComponent(url.pathname.slice('/api/live-odds/'.length));
      const match=/^(?:jra|nar)-(\d{4}-\d{2}-\d{2})-[^-/?]+-\d{2}$/.exec(id);
      if(!match)return Response.json({ok:false,error:'invalid race id'},{status:400});
      const asset=await env.ASSETS.fetch(new Request(url.origin+'/odds-sources/'+match[1]+'.json'));
      if(!asset.ok)throw Error('source manifest absent');
      const manifest=await asset.json();source=manifest.races&&manifest.races[id];date=match[1];
      if(manifest.version!=='arvexq-odds-sources-v1'||manifest.date!==match[1]||!source||source.id!==id||source.date!==match[1])
        return Response.json({ok:false,error:'verified source absent'},{status:404});
      const key=new Request(url.origin+url.pathname),cache=caches.default;
      const cached=await cacheLookup(cache,key,url.searchParams.has('force'));if(cached)return cached;
      retainedKey=new Request(url.origin+url.pathname+'?last-acquired=1');
      const result=await sourceOdds(source);
      const response=Response.json(result,{headers:{'Cache-Control':'public, max-age=15'}});
      cacheSave(cache,key,retainedKey,response,ctx);return response;
    }catch(_error){
      if(source){
        try{
          const retained=await retainedLookup(caches.default,retainedKey);
          const body=retained?{...(await retained.json()),oddsStatus:'saved',refreshFailed:true}:await savedOdds(env,url.origin,date,source);
          if(body)return Response.json(body,{headers:{'Cache-Control':'no-store'}});
        }catch{}
      }
      // For a verified race, source unavailability is data missingness, not an invalid page.
       // Keep 'ok:false' and empty odds: never invent a price or suppress the failure.
       return Response.json(source?{ok:false,race_id:source.id,odds:[],oddsStatus:'unavailable',refreshFailed:true,error:'official odds unavailable'}:{ok:false,error:'official odds source manifest unavailable',odds:[]},
         {status:source?200:503,headers:{'Cache-Control':'no-store'}});
    }
  }
};
