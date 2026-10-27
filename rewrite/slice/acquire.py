"""Bounded, cached public-page acquisition with exact-byte provenance."""
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class AcquisitionError(ValueError):
    pass


class Fetcher:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.rules = {}
        self.last = {}

    def _read(self, url):
        request = urllib.request.Request(url, headers={'User-Agent': 'ARVEXQ-Research/1.0 (read-only validation)'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(), dict(error.headers)

    def fetch(self, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'sports.yahoo.co.jp', 'keiba.rakuten.co.jp', 'www.jra.go.jp'}:
            raise AcquisitionError('unapproved source host')
        if parsed.hostname == 'www.jra.go.jp' and not parsed.path.startswith('/datafile/'):
            raise AcquisitionError('only static JRA datafile pages are allowed')
        key = hashlib.sha256(url.encode()).hexdigest()
        meta_path = self.directory / (key + '.json')
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            raw = (self.directory / meta['file']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta['sha256']:
                raise AcquisitionError('cached source hash mismatch')
            return raw.decode(meta.get('encoding', 'utf-8')), meta
        origin = f'{parsed.scheme}://{parsed.netloc}'
        if origin not in self.rules:
            status, raw, headers = self._read(origin + '/robots.txt')
            rules = RobotFileParser()
            if status == 200:
                rules.parse(raw.decode('utf-8').splitlines())
            elif status == 404:
                rules.parse([])
            else:
                raise AcquisitionError(f'robots unavailable: {status}')
            self.rules[origin] = rules
        rules = self.rules[origin]
        if not rules.can_fetch('ARVEXQ-Research', url):
            raise AcquisitionError('robots disallowed')
        delay = rules.crawl_delay('ARVEXQ-Research') or 1
        wait = delay - (time.monotonic() - self.last.get(origin, 0))
        if wait > 0:
            time.sleep(wait)
        status, raw, headers = self._read(url)
        self.last[origin] = time.monotonic()
        digest = hashlib.sha256(raw).hexdigest()
        filename = digest + '.html'
        (self.directory / filename).write_bytes(raw)
        encoding = 'cp932' if re.search(br'charset=[\"\']?Shift[_-]JIS', raw[:4096], re.I) else 'utf-8'
        meta = {'encoding':encoding, 'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                'status': status, 'sha256': digest, 'bytes': len(raw), 'file': filename,
                'content_type': headers.get('Content-Type', headers.get('content-type'))}
        if status != 200:
            raise AcquisitionError(f'provider HTTP {status}: {url}; raw retained: {filename}')
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        return raw.decode(encoding), meta
