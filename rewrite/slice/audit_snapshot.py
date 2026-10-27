"""Read-only local analysis of exported warehouse JSON, never rewrites originals."""
import base64
import gzip
import hashlib
import itertools
import json


def audit(raw, stored_sha256):
    snapshot=json.loads(raw)
    envelope=snapshot.get('arvexqFullPayload')
    result={'race_id':snapshot['id'],'stored_sha256':stored_sha256,
            'current_json_sha256':hashlib.sha256(raw.encode()).hexdigest(),
            'hash_basis_resolved':False,'warehouse_writes':0}
    if not envelope:
        return result
    original_bytes=gzip.decompress(base64.b64decode(envelope['gzipBase64'],validate=True))
    result['embedded_original_bytes']=len(original_bytes)
    result['embedded_original_length_verified']=len(original_bytes)==envelope['bytes']
    result['embedded_original_sha256']=hashlib.sha256(original_bytes).hexdigest()
    result['embedded_original_hash_verified']=result['embedded_original_sha256']==envelope['sha256']
    original=json.loads(original_bytes)
    changes={}
    for horse in snapshot.get('horses',[]):
        number=horse.get('horseNumber')
        old=next((h for h in original.get('horses',[]) if h.get('horseNumber')==number),None)
        if old:
            changes[str(number)]={'omitted_from_projection':sorted(k for k in old if k not in horse),
                                  'changed_values':sorted(k for k in old.keys() & horse.keys() if old[k]!=horse[k])}
    result['horse_projection_differences']=changes
    result['top_level_changes_except_envelope']=sorted(k for k in snapshot if k!='arvexqFullPayload' and snapshot[k]!=original.get(k))
    matched=[]
    for name,obj in [('stored',snapshot),('embedded',original)]:
        for sort,ascii,indent,sep in itertools.product((False,True),(False,True),(None,2),(None,(',',':'))):
            value=json.dumps(obj,sort_keys=sort,ensure_ascii=ascii,indent=indent,separators=sep)
            for suffix in ('','\n'):
                if hashlib.sha256((value+suffix).encode()).hexdigest()==stored_sha256:
                    matched.append({'object':name,'sort_keys':sort,'ensure_ascii':ascii,'indent':indent,'separators':sep,'suffix':suffix})
    result['matching_serializations']=matched
    result['hash_basis_resolved']=bool(matched)
    result['conclusion']='embedded originals verified; stored-column hash basis unresolved; do not modify originals'
    return result
