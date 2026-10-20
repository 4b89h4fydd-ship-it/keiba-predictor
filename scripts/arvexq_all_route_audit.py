#!/usr/bin/env python3
"""Exhaustive source-boundary census; does not call APIs or modify race data.

Counts and gaps are evidence, never a blanket claim of dynamic route success.
"""
from __future__ import annotations
import argparse, ast, hashlib, inspect, json, os, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(os.environ.get("ARVEXQ_AUDIT_ROOT",Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(ROOT))

def module_path(name):
    p=ROOT.joinpath(*name.split('.'))
    return p.with_suffix('.py') if p.with_suffix('.py').is_file() else (p/'__init__.py' if (p/'__init__.py').is_file() else p)

def scan():
    sources=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py','.js','.mjs','.cjs','.yml','.yaml'} and not any(x in {'.git','dist','node_modules','__pycache__'} for x in p.relative_to(ROOT).parts))
    definitions={}; names=defaultdict(list); calls={}; imports={}; missing=[]; network=[]; storage=[]; errors=[]
    jsimports=[]; workers=[]; frontend=[]; workflows=[]; embedded=[]; boundary_literals=[]
    source_hashes={}
    for p in sources:
        rel=p.relative_to(ROOT).as_posix(); raw=p.read_bytes();text=raw.decode(errors='replace');source_hashes[rel]=hashlib.sha256(raw).hexdigest()
        for i,line in enumerate(text.splitlines(),1):
            if re.search(r'https?://|/api/|getenv\(|os\.environ|DB\.prepare|\.execute\(',line):
                boundary_literals.append({'file':rel,'line':i,'code':line.strip(),'generatedCopy':rel=='arvexq/ui/static/app.js','testSource':rel.startswith('tests/')})
        if p.suffix=='.py':
            try: tree=ast.parse(text,filename=rel)
            except SyntaxError as e:errors.append({'file':rel,'error':str(e)});continue
            imported={}; deps=[]
            for assignment in tree.body:
                if not isinstance(assignment,ast.Assign):continue
                if not any(isinstance(t,ast.Name) and t.id=='SOURCE' for t in assignment.targets):continue
                try: embedded_text=ast.literal_eval(assignment.value)
                except (ValueError,TypeError):continue
                if not isinstance(embedded_text,str) or '\n' not in embedded_text:continue
                if not re.search(r'^\s*(?:def|class|from|import)\b',embedded_text,re.M):continue
                try: decoded=ast.parse(embedded_text)
                except SyntaxError as e:errors.append({'file':rel+'::SOURCE','error':str(e)});continue
                embedded.append({'file':rel,'sha256':hashlib.sha256(embedded_text.encode()).hexdigest(),'definitions':[{'name':n.name,'lineInDecodedSource':n.lineno,'calls':sorted(set(ast.unparse(c.func) for c in ast.walk(n) if isinstance(c,ast.Call)))} for n in ast.walk(decoded) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]})
            for n in ast.walk(tree):
                if isinstance(n,ast.ImportFrom) and n.module:
                    mod=n.module
                    if n.level:
                        package=list(p.relative_to(ROOT).parent.parts)
                        mod='.'.join(package[:len(package)-n.level+1]+n.module.split('.'))
                    if mod in {'arvexq','scripts'} or mod.startswith(('arvexq.','scripts.')):
                        target=module_path(mod);exists=target.is_file() or target.is_dir()
                        deps.append({'module':mod,'exists':exists,'line':n.lineno})
                        if not exists:missing.append({'file':rel,'line':n.lineno,'module':mod})
                        for a in n.names:imported[a.asname or a.name]=(target.relative_to(ROOT).as_posix(),a.name)
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    for a in n.names:
                        if a.name.startswith(('arvexq.','scripts.')):
                            target=module_path(a.name);exists=target.is_file() or target.is_dir()
                            deps.append({'module':a.name,'exists':exists,'line':n.lineno})
                            if not exists:missing.append({'file':rel,'line':n.lineno,'module':a.name})
            imports[rel]=deps
            for n in ast.walk(tree):
                if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                key=rel+':'+str(n.lineno)+':'+n.name
                entry={'file':rel,'line':n.lineno,'endLine':n.end_lineno,'name':n.name,'calls':[],'terminalOperations':[]}
                for c in ast.walk(n):
                    if not isinstance(c,ast.Call):continue
                    label=ast.unparse(c.func)
                    if isinstance(c.func,ast.Name):
                        entry['calls'].append(c.func.id)
                    if re.search(r'urlopen|requests\.|httpx\.|_request$|_get$|fetch_json|fetch\(',label):
                        entry['terminalOperations'].append({'line':c.lineno,'kind':'network-or-transport','call':label})
                    if isinstance(c.func,ast.Attribute) and c.func.attr in {'execute','executemany','commit','prepare','save','upsert_races','upsert_detail','mark_source'}:
                        entry['terminalOperations'].append({'line':c.lineno,'kind':'storage','call':label})
                definitions[key]=entry;names[n.name].append(key)
                for a,(f,symbol) in imported.items():
                    if a in entry['calls']:entry.setdefault('importedCalls',[]).append({'name':a,'file':f,'symbol':symbol})
        if p.suffix in {'.js','.mjs','.cjs'}:
            for m in re.finditer(r'(?:from\s*|require\s*\(|import\s*)[\'\"](\.[^\'\"]+)[\'\"]',text):
                target=(p.parent/m.group(1)).resolve();exists=target.is_file() or target.is_dir() or target.is_dir() or target.with_suffix('.js').is_file()
                jsimports.append({'file':rel,'line':text[:m.start()].count('\n')+1,'target':m.group(1),'exists':exists})
            for i,line in enumerate(text.splitlines(),1):
                if ('workers/' in rel or 'item_173/' in rel) and re.search(r'pathname|url\.path|/api/',line):workers.append({'file':rel,'line':i,'code':line.strip()})
                if rel.startswith('arvexq/') and re.search(r'\bfetch\(|edgeFetchJson\(|fetchJson\(|new XMLHttpRequest|EventSource\(',line):frontend.append({'file':rel,'line':i,'code':line.strip()})
        if rel.startswith('.github/workflows/'):
            import yaml
            d=yaml.safe_load(text) or {};triggers=d.get('on',d.get(True,{}));steps=[]
            for jname,j in (d.get('jobs') or {}).items():
                for s in j.get('steps',[]):
                    if 'run' not in s:continue
                    run=str(s['run']);refs=[]
                    for name in sorted(set(re.findall(r'(?:scripts|arvexq)/[\w/.-]+\.(?:py|js|mjs|cjs|sh)\b',run))):
                        refs.append({'path':name,'exists':(ROOT/name).is_file()})
                    steps.append({'job':jname,'name':s.get('name',''),'sources':refs,'runSha256':hashlib.sha256(run.encode()).hexdigest(),'mayMutateProduction':bool(re.search(r'wrangler.*deploy|/api/sync|POST|git push|migrate_full_snapshots',run))})
            workflows.append({'file':rel,'name':d.get('name'),'triggers':triggers,'steps':steps})
    # Resolve direct function calls without pretending ambiguous names are exact edges.
    for key,d in definitions.items():
        edges=[];unresolved=[]
        imported={x['name']:(x['file'],x['symbol']) for x in d.get('importedCalls',[])}
        for name in sorted(set(d.pop('calls'))):
            local=[k for k in names[name] if definitions[k]['file']==d['file']]
            if local:edges.extend(local);continue
            if name in imported:
                f,symbol=imported[name];matches=[k for k in names[symbol] if definitions[k]['file']==f]
                if matches:edges.extend(matches);continue
            # Component functions share app globals by the established installer.
            matches=[k for k in names[name] if definitions[k]['file'].startswith('arvexq/components/item_') and definitions[k]['file'].endswith('/implementation.py')]
            if len(matches)==1:edges.extend(matches)
            elif len(matches)>1:unresolved.append({'name':name,'kind':'ambiguous-component','candidates':matches})
            elif name not in dir(__builtins__):unresolved.append({'name':name,'kind':'external-or-dynamic'})
        d['resolvedDirectCalls']=sorted(set(edges));d['dynamicCalls']=unresolved
    # Import actual app without running ASGI lifespan / starting collectors.
    import app
    routes=[]
    for r in app.app.routes:
        endpoint=getattr(r,'endpoint',None)
        code=getattr(endpoint,'__code__',None)
        if not code:continue
        file=Path(code.co_filename).resolve()
        rel=file.relative_to(ROOT).as_posix() if file.is_relative_to(ROOT) else str(file)
        key=rel+':'+str(code.co_firstlineno)+':'+endpoint.__name__
        # Decorator firstline differs from def line; match file + symbol.
        matches=[k for k in names[endpoint.__name__] if definitions[k]['file']==rel]
        seen=set();pending=list(matches)
        while pending:
            k=pending.pop()
            if k in seen:continue
            seen.add(k);pending.extend(definitions[k]['resolvedDirectCalls'])
        routes.append({'methods':sorted(getattr(r,'methods',[]) or []),'path':r.path,'handler':endpoint.__name__,'owner':rel,'definitionKeys':matches,'reachableFunctionCount':len(seen),'reachableFunctions':sorted(seen),'terminalOperations':[dict(op,owner=definitions[k]['file'],function=definitions[k]['name']) for k in sorted(seen) for op in definitions[k]['terminalOperations']],'dynamicResolutionRemaining':sum(len(definitions[k]['dynamicCalls']) for k in seen),'verification':'registered-and-direct-source-traced; dynamic success not asserted'})
    # All 200 fixed owners, including reserved boxes, accounted individually.
    try:
        from arvexq.components.catalog import all_components
    except ModuleNotFoundError:
        all_components=lambda: []
    from arvexq.databanks.registry import registry
    components=[{'id':c['id'],'name':c['name'],'state':c['state'],'ownedModules':c.get('owned_modules',[]),'ownedDefinitions':c.get('owned_definitions',[]),'assets':c.get('assets',[])} for c in all_components()]
    providers={'registeredNames':registry.names(),'capabilities':registry.capability_map()}
    root_modules={'app.py','build_static.py'}
    root_modules.update(str(x['path']) for w in workflows for s in w['steps'] for x in s['sources'] if x['path'].endswith('.py'))
    reachable=set();todo=list(root_modules)
    while todo:
        f=todo.pop()
        if f in reachable:continue
        reachable.add(f)
        todo.extend(module_path(x['module']).relative_to(ROOT).as_posix() for x in imports.get(f,[]) if x['exists'])
    for m in missing:m['workflowOrAppImportReachable']=m['file'] in reachable
    summary={'sourceFiles':len(source_hashes),'registeredRoutes':len(routes),'components':len(components),'workflows':len(workflows),'pythonDefinitions':len(definitions),'pythonMissingInternalImports':len(missing),'missingWorkflowSourceFiles':sum(not x['exists'] for w in workflows for s in w['steps'] for x in s['sources']),'missingJsRelativeImports':sum(not x['exists'] for x in jsimports),'frontendTransportSites':len(frontend),'workerRouteLines':len(workers),'syntaxErrors':len(errors),'productionVerified':False,'everyDynamicBranchVerified':False}
    return {'summary':summary,'gitHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceHashes':source_hashes,'routes':routes,'components':components,'providers':providers,'workflows':workflows,'missingPythonImports':missing,'jsImports':jsimports,'workerRouteSites':workers,'frontendTransportSites':frontend,'pythonDefinitions':definitions,'syntaxErrors':errors,'embeddedSources':embedded,'boundaryLiteralSites':boundary_literals}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    result=scan();Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n');print(json.dumps(result['summary'],ensure_ascii=False))
