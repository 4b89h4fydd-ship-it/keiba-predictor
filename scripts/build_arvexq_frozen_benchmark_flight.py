from pathlib import Path
import base64,io,zipfile
files=['scripts/export_motherduck_frozen_ranking.py','arvexq/research/ranking_benchmark.py','arvexq/research/ranking_challenger.py','arvexq/research/ranking_feature_signals.py','arvexq/prediction/mass_training_store.py','arvexq/prediction/mass_training_dataset.py','arvexq/prediction/mass_feature_transport.py','arvexq/prediction/mass_feature_selection.py']
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.writestr(p,Path(p).read_bytes())
source='import base64,io,zipfile,tempfile,sys,json,hashlib\nfrom pathlib import Path\nimport duckdb\nBUNDLE='+repr(base64.b64encode(b.getvalue()).decode())+'\n'
source+='''
def main():
 root=Path(tempfile.mkdtemp());zipfile.ZipFile(io.BytesIO(base64.b64decode(BUNDLE))).extractall(root)
 for sub in ('arvexq','arvexq/research','arvexq/prediction','scripts'):(root/sub/'__init__.py').write_text('')
 sys.path.insert(0,str(root))
 from scripts.export_motherduck_frozen_ranking import QUERY,export
 from arvexq.research.ranking_benchmark import benchmark
 c=duckdb.connect('md:')
 path=root/'frozen.jsonl'
 audit=export(c.execute(QUERY,[None,None,None,None]),path)
 print('FROZEN_EXPORT',json.dumps(audit),flush=True)
 rows=[json.loads(x) for x in path.read_text().splitlines()]
 results=benchmark(rows,root/'models')
 c.execute("CREATE TABLE IF NOT EXISTS arvexq_history_research.main.frozen_benchmark_execution_v1 (execution_id VARCHAR, payload JSON)")
 import uuid
 execution=str(uuid.uuid4())
 model_artifacts={str(p.relative_to(root/'models')):base64.b64encode(p.read_bytes()).decode() for p in (root/'models').rglob('*') if p.is_file()}
 record=dict(model_artifacts_base64=model_artifacts,audit=audit,reports=results,code_bundle_sha=hashlib.sha256(base64.b64decode(BUNDLE)).hexdigest(),data_sha=hashlib.sha256(path.read_bytes()).hexdigest(),productionChanged=False)
 c.execute('INSERT INTO arvexq_history_research.main.frozen_benchmark_execution_v1 VALUES (?,?)',[execution,json.dumps(record)])
 print('DONE',execution,json.dumps(record),flush=True)
if __name__=='__main__':main()
'''
Path('/tmp/arvexq_frozen_flight.py').write_text(source)
print(len(source))
