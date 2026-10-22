#!/usr/bin/env python3
"""Run Stage 4 tests with temporary stores and no external sockets.

This never starts a server or deploys. Optional baseline must be a separate
checkout of main 6f21f2e595df17f840c785c31a9f1c5a802bb169.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ISOLATION = '''import os,socket,ipaddress
for key in ['ARVEXQ_DATA_CORE','ARVEXQ_BOOTSTRAP_WARM','RACEDB_AUTO_UPDATE','RACEDB_AUTO_ODDS']:
 os.environ[key]='0'
def checked(fn):
 def connect(sock,address):
  if not isinstance(address,tuple):return fn(sock,address)
  try: allowed=ipaddress.ip_address(address[0]).is_loopback
  except ValueError: allowed=address[0]=='localhost'
  if not allowed:raise RuntimeError('Stage4 offline: external socket blocked')
  return fn(sock,address)
 return connect
socket.socket.connect=checked(socket.socket.connect)
socket.socket.connect_ex=checked(socket.socket.connect_ex)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New local evidence directory')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    baseline = args.baseline.resolve() if args.baseline else None
    if baseline:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=baseline, text=True).strip()
        if sha != '6f21f2e595df17f840c785c31a9f1c5a802bb169':
            parser.error('baseline SHA differs from the reviewed Stage 4 baseline')
    with tempfile.TemporaryDirectory(prefix='arvexq-stage4-') as temporary:
        temp = Path(temporary)
        (temp / 'sitecustomize.py').write_text(ISOLATION)
        env = dict(os.environ, PYTHONPATH=str(temp) + os.pathsep + '.', KEIBA_DATA_DIR=str(temp / 'candidate-data'))
        for key in ('RACEDB_PATH', 'DAY_BUNDLE_DB_PATH'):
            env.pop(key, None)
        commands = [
            ('pytest', [sys.executable, '-m', 'pytest', 'tests', '-q', '--disable-warnings', '--tb=short', '--junitxml='+str(output/'pytest.xml')]),
            ('node-contracts', ['node', 'tests/stage4_box_routes.mjs'] + ([str(baseline)] if baseline else [])),
            ('race-loading', ['node', 'tests/race_loading_smoke.js']),
            ('horse-status', ['node', 'tests/horse_realtime_sync.mjs']),
            ('audit', [sys.executable, 'scripts/arvexq_independence_audit.py']),
        ]
        failed = []
        for name, command in commands:
            with (output / (name+'.log')).open('w') as log:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            if result.returncode:
                failed.append(name)
        if baseline:
            values = []
            for label, cwd in [('candidate', ROOT), ('baseline', baseline)]:
                runenv = dict(env, KEIBA_DATA_DIR=str(temp / (label+'-probe-data')))
                result = subprocess.run([sys.executable, str(ROOT/'tests/stage4_runtime_probe.py')], cwd=cwd, env=runenv, capture_output=True, text=True, timeout=60)
                (output/(label+'-runtime.json')).write_text(result.stdout)
                if result.returncode:
                    failed.append(label+'-probe')
                    (output/(label+'-runtime.stderr')).write_text(result.stderr)
                else:
                    values.append(json.loads(result.stdout))
            if len(values) != 2 or values[0] != values[1]:
                failed.append('runtime-differential')
        (output/'result.json').write_text(json.dumps({'failed':failed,'external_sockets':'blocked','production':False},indent=2)+'\n')
        print(json.dumps({'failed': failed, 'output': str(output)}))
        return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
