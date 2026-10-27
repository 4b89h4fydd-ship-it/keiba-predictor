"""Append-only retrospective artifacts; never claims to seal pre-off originals."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


class Store:
    def __init__(self, path, read_only=False):
        from pathlib import Path
        self.db = sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True) if read_only else sqlite3.connect(path)
        if read_only:
            return
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS runs(
          race_id TEXT PRIMARY KEY, input BLOB NOT NULL, output BLOB NOT NULL,
          input_sha256 TEXT NOT NULL, output_sha256 TEXT NOT NULL,
          generated_at TEXT NOT NULL, analysis_type TEXT NOT NULL CHECK(analysis_type='retrospective'));
        CREATE TRIGGER IF NOT EXISTS runs_no_update BEFORE UPDATE ON runs
          BEGIN SELECT RAISE(ABORT,'immutable research artifact'); END;
        CREATE TRIGGER IF NOT EXISTS runs_no_delete BEFORE DELETE ON runs
          BEGIN SELECT RAISE(ABORT,'immutable research artifact'); END;
        ''')

    def close(self):
        self.db.close()

    def save(self, race, analysis):
        if analysis['race_id'] != race['id'] or analysis['analysis_type'] != 'retrospective' or analysis['production_eligible']:
            raise ValueError('artifact identity/mode mismatch')
        raw, output = encode(race), encode(analysis)
        ih, oh = digest(race), digest(analysis)
        existing = self.db.execute('SELECT input_sha256,output_sha256 FROM runs WHERE race_id=?',(race['id'],)).fetchone()
        if existing:
            if existing != (ih,oh):
                raise ValueError('immutable artifact collision')
            return self.read(race['id'])
        with self.db:
            self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?)',
                            (race['id'],raw,output,ih,oh,datetime.now(timezone.utc).isoformat(),'retrospective'))
        return self.read(race['id'])

    def read(self, race_id):
        row = self.db.execute('SELECT input,output,input_sha256,output_sha256,generated_at FROM runs WHERE race_id=?',(race_id,)).fetchone()
        if not row:
            raise KeyError(race_id)
        if hashlib.sha256(row[0]).hexdigest()!=row[2] or hashlib.sha256(row[1]).hexdigest()!=row[3]:
            raise ValueError('persisted artifact hash mismatch')
        race, analysis = json.loads(row[0]), json.loads(row[1])
        if race['id'] != race_id or analysis['race_id'] != race_id:
            raise ValueError('persisted artifact race mismatch')
        return {'ok':True,'race':race,'analysis':analysis,
                'receipt':{'input_sha256':row[2],'analysis_sha256':row[3],'generated_at':row[4],
                           'analysis_type':'retrospective','pre_off_original':False}}

    def list(self):
        return [self.read(row[0]) for row in self.db.execute('SELECT race_id FROM runs ORDER BY race_id').fetchall()]
