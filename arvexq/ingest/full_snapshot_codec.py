"""Lossless compression of the entire detail; compact fields are only an index.

The original UTF-8 JSON, all careers, marks, bets and unknown future fields are
restored and hash-checked. No model computation or archival truncation occurs.
"""
import base64
import copy
import gzip
import hashlib
import json

VERSION='arvexq-full-payload-v1'
KEY='arvexqFullPayload'
KEEP={'preRacePrediction','preRaceBet','preRaceBetPlan','morningTicketEvidence',
      'morningPicks','environmentMeta','volatility','preparedMeta','result',
      'modelRevisions','authorizedRevisions','massFeatureArchive','dataReadiness'}

def pack_raw(raw):
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('detail must be an object')
    data=raw.encode('utf-8')
    thin={key:copy.deepcopy(item) for key,item in value.items()
          if key!=KEY and (key in KEEP or not isinstance(item,(dict,list)))}
    if isinstance(value.get('horses'),list):
        thin['horses']=[{key:copy.deepcopy(item) for key,item in horse.items()
                        if key=='careerTransport' or not isinstance(item,(dict,list))}
                       for horse in value['horses'] if isinstance(horse,dict)]
    thin[KEY]={'version':VERSION,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
               'gzipBase64':base64.b64encode(gzip.compress(data,compresslevel=9,mtime=0)).decode('ascii')}
    assert unpack_raw(thin)==raw
    return thin

def unpack_raw(value):
    ref=value[KEY]
    if ref.get('version')!=VERSION or not 0<int(ref.get('bytes',0))<=100000000:
        raise ValueError('invalid full snapshot envelope')
    data=gzip.decompress(base64.b64decode(ref['gzipBase64'],validate=True))
    if len(data)!=ref['bytes'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:
        raise ValueError('full snapshot restore mismatch')
    return data.decode('utf-8')

def pack_detail(value):
    if KEY in value:value=json.loads(unpack_raw(value))
    return pack_raw(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False))

def unpack_detail(value):
    return json.loads(unpack_raw(value)) if KEY in value else copy.deepcopy(value)
