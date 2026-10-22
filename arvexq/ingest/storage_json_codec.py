"""Lossless D1 JSON storage. Public JSON and its original SHA remain unchanged."""
import base64
import gzip
import hashlib
import json

VERSION = 'arvexq-storage-gzip-v1'


def encode(raw):
    data = raw.encode('utf-8')
    packed = json.dumps({'storageEncoding': VERSION, 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest(),
                         'gzipBase64': base64.b64encode(gzip.compress(data, compresslevel=9, mtime=0)).decode('ascii')},
                        separators=(',', ':'))
    return packed if len(packed.encode()) < len(data) else raw


def decode(stored, max_bytes=1_000_000):
    value = json.loads(stored)
    if not isinstance(value, dict) or value.get('storageEncoding') != VERSION:
        return stored
    size = value.get('bytes')
    if type(size) is not int or not 0 < size <= max_bytes:
        raise ValueError('invalid stored JSON length')
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(value['gzipBase64'], validate=True))) as stream:
        data = stream.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != value.get('sha256'):
        raise ValueError('stored JSON restore mismatch')
    return data.decode('utf-8')
