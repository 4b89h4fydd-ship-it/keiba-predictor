const CACHE="kraiz-shell-v137-inlinecss";
const STATIC=[
  "/index.html",
  "/app-v137.js",
  "/manifest-kraiz-v130.webmanifest",
  "/kraiz-icon-192.png",
  "/kraiz-icon-512.png",
  "/kraiz-racing-hero.webp"
];
const LAST_PAGE="/__kraiz_last_page_v137__";

self.addEventListener("install",event=>{
  event.waitUntil(
    caches.open(CACHE).then(cache=>
      Promise.all(STATIC.map(url=>fetch(url,{cache:"reload"}).then(r=>{
        if(r&&r.ok)return cache.put(url,r.clone())
      }).catch(()=>null)))
    ).then(()=>self.skipWaiting())
  )
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())

  )
});

self.addEventListener("fetch",event=>{
  const req=event.request;
  if(req.method!=="GET")return;
  const url=new URL(req.url);
  if(url.origin!==location.origin)return;
  if(url.pathname.startsWith("/api/"))return;

  if(req.mode==="navigate"){
    event.respondWith(
      fetch(req,{cache:"no-store"})
        .then(async r=>{
          if(!r||!r.ok)throw Error("navigation "+(r&&r.status));
          const cache=await caches.open(CACHE);await cache.put(LAST_PAGE,r.clone());return r
        })
        .catch(async ()=>{
          const cache=await caches.open(CACHE);
          return (await cache.match(LAST_PAGE))||(await cache.match("/index.html"))||new Response("通信状態を確認して再読み込みしてください",{status:503,headers:{"Content-Type":"text/plain; charset=utf-8"}})
        })
    );
    return
  }

  if(STATIC.includes(url.pathname)){
    event.respondWith(
      caches.match(req).then(cached=>cached||fetch(req,{cache:"reload"}).then(r=>{
        if(r&&r.ok)caches.open(CACHE).then(c=>c.put(req,r.clone()));
        return r
      }))
    )
  }
});