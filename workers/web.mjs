import {sourceOdds} from './live_odds.mjs';
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(!url.pathname.startsWith('/api/live-odds/'))return env.ASSETS.fetch(request);
    if(request.method!=='GET')return new Response('Method not allowed',{status:405});
    try{
      const id=decodeURIComponent(url.pathname.slice('/api/live-odds/'.length));
      const match=/^(?:jra|nar)-(\d{4}-\d{2}-\d{2})-[^-/?]+-\d{2}$/.exec(id);
      if(!match)return Response.json({ok:false,error:'invalid race id'},{status:400});
      const asset=await env.ASSETS.fetch(new Request(url.origin+'/odds-sources/'+match[1]+'.json'));
      if(!asset.ok)throw Error('source manifest absent');
      const manifest=await asset.json(),source=manifest.races&&manifest.races[id];
      if(manifest.version!=='arvexq-odds-sources-v1'||manifest.date!==match[1]||!source||source.id!==id||source.date!==match[1])
        return Response.json({ok:false,error:'verified source absent'},{status:404});
      const key=new Request(url.origin+url.pathname),cache=caches.default;
      const cached=await cache.match(key);if(cached&&!url.searchParams.has('force'))return cached;
      const result=await sourceOdds(source);
      const response=Response.json(result,{headers:{'Cache-Control':'public, max-age=15'}});
      ctx.waitUntil(cache.put(key,response.clone()));return response;
    }catch(_error){
      return Response.json({ok:false,error:'official odds unavailable',odds:[]},{status:503,headers:{'Cache-Control':'no-store'}});
    }
  }
};
