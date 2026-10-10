import {sourceOdds} from './live_odds.mjs';
import {savedOdds} from './saved_odds.mjs';
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
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
      const cached=await cache.match(key);if(cached&&!url.searchParams.has('force'))return cached;
      retainedKey=new Request(url.origin+url.pathname+'?last-acquired=1');
      const result=await sourceOdds(source);
      const response=Response.json(result,{headers:{'Cache-Control':'public, max-age=15'}});
      const retained=response.clone();retained.headers.set('Cache-Control','public, max-age=604800');
      ctx.waitUntil(Promise.all([cache.put(key,response.clone()),cache.put(retainedKey,retained)]));return response;
    }catch(_error){
      if(source){
        try{
          const retained=retainedKey&&await caches.default.match(retainedKey);
          const body=retained?{...(await retained.json()),oddsStatus:'saved',refreshFailed:true}:await savedOdds(env,url.origin,date,source);
          if(body)return Response.json(body,{headers:{'Cache-Control':'no-store'}});
        }catch{}
      }
      return Response.json({ok:false,error:'official odds unavailable',odds:[]},{status:503,headers:{'Cache-Control':'no-store'}});
    }
  }
};
