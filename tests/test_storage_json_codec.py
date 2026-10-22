import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from arvexq.ingest.storage_json_codec import encode, decode


class StorageCodecTests(unittest.TestCase):
    def test_exact_unicode_numeric_spellings_and_unknown_fields(self):
        raw = '{"number":1.0000,"future":' + json.dumps('日本語🐎' * 2000, ensure_ascii=False) + '}'
        packed = encode(raw)
        self.assertLess(len(packed.encode()), len(raw.encode()))
        self.assertEqual(decode(packed), raw)
        self.assertEqual(decode(raw), raw)
        self.assertEqual(encode('{}'), '{}')
        bad = json.loads(packed)
        bad['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            decode(json.dumps(bad))
        bad['bytes'] = 1
        with self.assertRaises(ValueError):
            decode(json.dumps(bad))

    @unittest.skipUnless(shutil.which('node'), 'Node required for cross-runtime verification')
    def test_python_storage_is_restored_byte_exactly_by_worker(self):
        detail = json.loads((Path(__file__).parent / 'fixtures/forecast_revision_transport.json').read_text())['detail']
        raw = json.dumps(detail['forecastRevisions'][0], ensure_ascii=False, separators=(',', ':'))
        code = """import fs from 'node:fs';import {webcrypto} from 'node:crypto';
globalThis.crypto??=webcrypto;
const {restoreStoredJSON,compressStoredJSON}=await import('./workers/api_forecast_revisions.mjs');
const raw=await restoreStoredJSON(fs.readFileSync(0,'utf8'));
if(await restoreStoredJSON(await compressStoredJSON(raw))!==raw)throw Error('worker round trip mismatch');
process.stdout.write(raw);"""
        restored = subprocess.run(['node', '--input-type=module', '-e', code], input=encode(raw),
                                  text=True, capture_output=True, check=True).stdout
        self.assertEqual(restored, raw)
        self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(), hashlib.sha256(raw.encode()).hexdigest())
