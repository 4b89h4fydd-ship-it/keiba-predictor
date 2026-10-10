/* Read-only, hash-verified existing originals. No forecast reconstruction. */
(function(root){
  'use strict';
  var days=Object.create(null),jobs=Object.create(null);
  function available(date,id,fetchJson){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(String(date||''))||!id||
       typeof DecompressionStream==='undefined')return Promise.resolve(null);
    var key=date+'|'+id;
    if(!days[date])days[date]=fetchJson('/saved-snapshots/'+date+'.json',6500).then(function(m){
      if(!m||m.version!=='arvexq-saved-snapshots-v1'||m.date!==date||!m.races)throw Error('invalid snapshot manifest');
      return m;
    }).catch(function(){delete days[date];return null});
    if(!jobs[key])jobs[key]=days[date].then(async function(m){
      var ref=m&&m.races[String(id)];if(!ref)return null;
      if(!/^[a-f0-9]{64}\.json$/.test(ref.file)||ref.file!==ref.sha256+'.json')throw Error('invalid snapshot reference');
      var e=await fetchJson('/saved-snapshots/'+ref.file,9000);
      if(!e||e.version!=='arvexq-saved-snapshot-v1'||e.sha256!==ref.sha256||e.bytes!==ref.bytes||e.bytes>100000000)
        throw Error('invalid snapshot envelope');
      var bytes=Uint8Array.from(atob(e.gzipBase64),function(c){return c.charCodeAt(0)});
      var raw=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      if(raw.byteLength!==e.bytes)throw Error('snapshot restored size mismatch');
      var digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(function(n){return n.toString(16).padStart(2,'0')}).join('');
      if(digest!==ref.sha256)throw Error('snapshot restored hash mismatch');
      var d=JSON.parse(new TextDecoder().decode(raw)),seen=new Set();
      if(d.id!==String(id)||d.date!==date||!Array.isArray(d.horses)||d.horses.length<2)throw Error('snapshot race mismatch');
      d.horses.forEach(function(h){if(!Number.isInteger(h.horseNumber)||h.horseNumber<1||!h.name||seen.has(h.horseNumber))throw Error('snapshot roster invalid');seen.add(h.horseNumber)});
      return Object.assign({},d,{_savedSnapshotFallback:true});
    }).catch(function(){delete jobs[key];return null});
    return jobs[key];
  }
  root.ARVEXQSavedSnapshot=Object.freeze({available:available});
})(typeof window!=='undefined'?window:globalThis);
