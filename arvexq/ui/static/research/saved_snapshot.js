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
      if(root.ARVEXQRaceIdentity)root.ARVEXQRaceIdentity.remember(d);
      return Object.assign({},d,{_savedSnapshotFallback:true,_savedSnapshotSHA:ref.sha256,_savedPreoffOriginal:d.preRacePrediction||null,
        _savedOriginalField:d.horses.map(function(h){return {horseNumber:h.horseNumber,scratched:!!h.scratched,withdrawn:!!h.withdrawn,status:h.status||''}})});
    }).catch(function(){delete jobs[key];return null});
    return jobs[key];
  }
  function marks(r){
    // Only a hash-verified archive can expose a provisional pre-off original.
    // Its frozen=false flag remains unchanged; this is a read-only saved opinion.
    if(!r||!r._savedSnapshotFallback)return null;
    var q=r._savedPreoffOriginal,seen=new Set(),known=new Set((r.horses||[]).map(function(h){return h.horseNumber}));
    var post=Date.parse(r.date+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00');
    if(!q||q.raceId!==r.id||q.raceDate!==r.date||!Array.isArray(q.horses)||q.horses.length<2||
       !(Number(q.capturedAtEpoch)>0)||!Number.isFinite(post)||Number(q.capturedAtEpoch)*1000>=post)return null;
    for(var i=0;i<q.horses.length;i++){
      var h=q.horses[i];
      if(!h||!known.has(h.horseNumber)||seen.has(h.horseNumber)||
         ['', '◎','○','▲','☆+','☆','△','注'].indexOf(String(h.mark||''))<0)return null;
      seen.add(h.horseNumber);
    }
    // Original predictions legitimately omit withdrawn runners. Every active
    // horse still needs a recorded row; an incomplete live field cannot pass.
    var active=(r._savedOriginalField||r.horses||[]).filter(function(h){return !h.scratched&&!h.withdrawn&&!/取消|除外|欠場/.test(String(h.status||''))});
    if(active.some(function(h){return !seen.has(h.horseNumber)})||q.horses.filter(function(h){return h.mark==='◎'}).length>1)return null;
    return Object.assign({},q,{version:'arvexq-saved-preoff-marks-v1'});
  }
  root.ARVEXQSavedSnapshot=Object.freeze({available:available,marks:marks});
})(typeof window!=='undefined'?window:globalThis);
