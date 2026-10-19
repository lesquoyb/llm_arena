"""Standalone loopback workshop; worker processes own all mutable scientific state."""
import json
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from arena.calibration import defaults, validate
from arena.calibration_documents import effective as effective_documents, originals as original_documents
from arena.core import ROOT, ArenaError, read_json, write_json, digest, file_hash
from arena.preparation import local_path
from arena.tool_schemas import TOOLS
from .data import Store
from .provider_output import blocks

STATIC = Path(__file__).parent/'static'


def decision_reason(row, parent, config, candidate):
    if candidate==0: return 'Reference candidate. The analyst has not edited this baseline.'
    if not row: return 'The proposal has not completed its paired validation yet.'
    after=row['report'];before=(parent or {}).get('report',{})
    if row['accepted']:
        if after.get('final_valid') and not before.get('final_valid'):
            return 'Kept: the candidate restored valid submitted strategies.'
        return 'Kept: the candidate passed the validity and paired score checks and improved the configured objective.'
    if not after.get('final_valid'): return 'Rejected: the candidate did not finish with valid submitted strategies.'
    if (after.get('tokens') is None)!=(before.get('tokens') is None):
        return 'Rejected: target token measurements are not comparable between candidate and incumbent.'
    if config.get('evaluation',{}).get('mode')=='hybrid':
        return 'Rejected: the candidate did not improve combat performance or the Laya tie-break within the allowed combat tolerance.'
    tolerance=config['optimizer']['score_tolerance']
    for new,old in zip(after.get('replicates',[]),before.get('replicates',[])):
        if new['rounds'][-1]['validation']['score'] < old['rounds'][-1]['validation']['score']-tolerance:
            return 'Rejected: at least one paired replicate lost more validation score than the permitted tolerance.'
    return 'Rejected: the configured objective did not improve. It combines validation score, convergence speed and token use.'


def saved_config(directory):
    path=directory/'input.json'
    return read_json(path) if path.exists() else read_json(directory/'study.json')['config']


class Workshop:
    def __init__(self, root, store=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.store = store or Store()
        self.lock = threading.RLock()
        self.processes = {}
        self.errors = {}

    def listing(self):
        rows = []
        directories={p.parent for pattern in ('*/input.json','*/study.json') for p in self.root.glob(pattern)}
        for directory in sorted(directories, reverse=True):
            state = read_json(directory/'study.json') if (directory/'study.json').exists() else {}
            process = self.processes.get(directory.name)
            running = bool(process and process.poll() is None)
            config=saved_config(directory)
            if not running and state.get('status') == 'running': state['status']='stopped'
            if process and process.poll() not in (None,0) and state.get('status') not in {'blocked','completed'}:
                state['status']='stopped' if directory.name in self.errors else 'worker_failed'
            comparison = {k:v for k,v in config.items() if k not in {'name','prompt','tools','analyst','optimizer','reference_documents'}}
            comparison['objective']={k:v for k,v in config['optimizer'].items() if k in {'round_penalty','token_penalty_per_million','score_tolerance'}}
            first=directory/'trials/000/calibration.json'
            comparison['scientific_identity']=read_json(first).get('scientific_identity') if first.exists() else None
            rows.append({'id':directory.name, 'name':config['name'], 'comparison_key':digest(comparison), 'running':running,
                         'status':'running' if running else self.errors.get(directory.name) or state.get('status','stopped'),
                         'incumbent':state.get('incumbent'), 'trials':[{**t,'report':{k:v for k,v in t['report'].items() if k not in {'replicates'}}} for t in state.get('trials', [])], 'audit':state.get('audit'),
                         'error':state.get('error'), 'automatic':state.get('automatic', False)})
        return rows

    def start(self, config, automatic, identifier=None, keys=None):
        if type(automatic) is not bool: raise ArenaError("Workflow must be a boolean")
        config = validate(config)
        if automatic and config['max_rounds'] is None:
            raise ArenaError('Automatic candidate selection needs finite rounds; choose manual prompt editing to stop rounds manually')
        if keys is not None and (not isinstance(keys,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in keys.items())):
            raise ArenaError('Credentials must map model IDs to key strings')
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ArenaError('A calibration is running; stop it before starting another')
            if config['target']['provider'] != 'mock' or (automatic and config.get('analyst',{}).get('provider','mock') != 'mock'):
                if not config['spending']['allow_paid_calls']:
                    raise ArenaError('Activate API calls explicitly in the spending settings')
            identifier = identifier or time.strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:6]
            directory = local_path(self.root, identifier)
            if identifier in self.processes and self.processes[identifier].poll() is None:
                raise ArenaError('Study is already running')
            directory.mkdir(parents=True, exist_ok=True)
            if (directory/'input.json').exists() and read_json(directory/'input.json') != config:
                raise ArenaError('Resume uses the exact frozen configuration; fork to edit')
            write_json(directory/'input.json', config)
            env = os.environ.copy()
            for model in [config['target'], config.get('analyst')]:
                if not model or model['provider'] == 'mock': continue
                key = (keys or {}).get(model['id']) or self.store.secrets.get(model['api_key_env'])
                if key:
                    if not isinstance(key,str) or len(key)>8192: raise ArenaError('Invalid credential')
                    env[model['api_key_env']] = key
            cmd = [sys.executable, '-m', 'arena', 'calibrate', 'run', str(directory/'input.json'), '--out', str(directory)]
            if automatic: cmd.append('--automatic')
            options = {'start_new_session':True} if os.name != 'nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
            with (directory/'worker.log').open('ab') as log:
                self.processes[identifier] = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, **options)
            self.errors.pop(identifier, None)
            return {'id':identifier}

    def stop(self, identifier):
        with self.lock:
            process = self.processes.get(identifier)
            if process and process.poll() is None:
                self.errors[identifier]='stopped'
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], check=False, capture_output=True)
                else: os.killpg(process.pid, signal.SIGTERM)
            return {'stopped':identifier}

    def get(self, route, query):
        value = lambda key, default='': query.get(key,[default])[0]
        if route == '/api/bootstrap':
            from arena.feedback import available_tools
            from arena.presets import simple_scenario, participant_scenario, dream_team_scenario
            scenarios={'simple':simple_scenario(),'llm-team':participant_scenario()}
            try: scenarios['dream-team']=dream_team_scenario()
            except (ArenaError,OSError): pass
            return {'token':self.token,'config':defaults(),'participants':self.store.participants(),
                    'reference_documents':original_documents(),
                    'tools':available_tools({'calibration':{'tools':[t['name'] for t in TOOLS]}}),'scenarios':scenarios}
        if route == '/api/studies': return self.listing()
        directory = local_path(self.root,value('study'))
        if route == '/api/study':
            proposal_paths={p.parent:(p.parent/'proposal.json' if (p.parent/'proposal.json').exists() else p) for pattern in ('proposals/*/proposal.json','proposals/*/proposal-draft.json') for p in directory.glob(pattern)}
            return {'runtime_status':next((row['status'] for row in self.listing() if row['id']==directory.name), 'stopped'), 'config':saved_config(directory), 'state':read_json(directory/'study.json') if (directory/'study.json').exists() else {},
                    'progress': [{'trial': p.parent.name, 'value':read_json(p)} for p in directory.glob('trials/*/progress.json')],
                    'active_reports':{p.parent.relative_to(directory).as_posix():read_json(p) for p in directory.glob('trials/*/report.json')},
                    'trial_directories':[p.parent.relative_to(directory).as_posix() for p in sorted(directory.glob('trials/*/journal.sqlite'),key=lambda p:int(p.parent.name))],
                    'proposal_directories':[p.parent.relative_to(directory).as_posix() for p in sorted(directory.glob('proposals/*/journal.sqlite'),key=lambda p:int(p.parent.name))],
                    'proposals':[{'directory':p.parent.relative_to(directory).as_posix(),'candidate':int(p.parent.name)+1,
                                  'rationale':read_json(p).get('rationale',''),'guard_status':read_json(p.parent/'guard.json').get('status') if (p.parent/'guard.json').exists() else None} for p in sorted(proposal_paths.values(),key=lambda p:int(p.parent.name))]}
        if route == '/api/tool-requests':
            return [{'candidate':int(path.parent.name)+1, 'requests':read_json(path).get('tool_requests',[])}
                    for path in sorted(directory.glob('proposals/*/proposal.json'),key=lambda p:int(p.parent.name))]
        if route == '/api/log':
            path = directory/'worker.log'
            with path.open('rb') as stream:
                stream.seek(max(0,path.stat().st_size-128000))
                return {'content':stream.read().decode('utf-8',errors='replace')}
        trial = local_path(directory,value('trial'))
        if route in {'/api/candidate','/api/proposal'}:
            state=read_json(directory/'study.json')
            candidate=int(trial.name)
            row=next((t for t in state.get('trials',[]) if t['directory']==f'trials/{candidate:03}'),None)
            parent_index=row.get('parent') if row else state.get('active_parent',state.get('incumbent'))
            parent=state['trials'][parent_index] if parent_index is not None else None
            comparison_index=row.get('comparison_parent',parent_index) if row else state.get('incumbent')
            comparison=state['trials'][comparison_index] if comparison_index is not None else None
            before=read_json(directory/parent['directory']/'calibration.json')['config'] if parent else state['config']
            if route=='/api/proposal':
                proposal=read_json(trial/'proposal.json' if (trial/'proposal.json').exists() else trial/'proposal-draft.json')
                frozen={**before,**{k:proposal[k] for k in ('prompt','tools','reference_documents') if k in proposal}}
            else:
                proposal_path=directory/'proposals'/f'{candidate:03}'/'proposal.json'
                proposal=read_json(proposal_path) if proposal_path.exists() else read_json(proposal_path.with_name('proposal-draft.json')) if proposal_path.with_name('proposal-draft.json').exists() else {}
                frozen=read_json(trial/'calibration.json')['config']
            import difflib
            before_root=directory/parent['directory'] if parent else directory/'trials/000'
            before_documents={name:(before_root/'corpus'/name).read_text(encoding='utf-8') if (before_root/'corpus'/name).exists() else text for name,text in effective_documents(before).items()}
            after_root=directory/'trials'/f'{candidate:03}'
            after_documents={name:(after_root/'corpus'/name).read_text(encoding='utf-8') if (after_root/'corpus'/name).exists() else frozen.get('reference_documents',{}).get(name,before_documents.get(name,text)) for name,text in effective_documents(frozen).items()}
            guard_path=directory/'proposals'/f'{candidate:03}'/'guard.json'
            return {'guard':read_json(guard_path) if guard_path.exists() else None,'guard_enabled':state['config'].get('proposal_guard',{}).get('enabled',False), 'config':frozen,'current_best':state.get('incumbent')==candidate,'comparison_candidate':comparison_index+1 if comparison_index is not None else None,'candidate':candidate+1,'baseline':candidate==0,
                    'decision_reason':('Not evaluated: the proposal check returned '+read_json(guard_path)['status']+'.') if not row and guard_path.exists() and read_json(guard_path)['status']!='approved' else decision_reason(row,comparison,state['config'],candidate),
                    'decision':'Baseline' if candidate==0 else 'Kept' if row and row['accepted'] else 'Rejected' if row else 'Blocked by proposal check' if guard_path.exists() and read_json(guard_path)['status']!='approved' else 'Pending evaluation',
                    'rationale':proposal.get('rationale') or (row.get('rationale') if row else 'Candidate evaluation is in progress.'),
                    'source_candidate':parent_index+1 if parent_index is not None else 1, 'search':row.get('search') if row else None, 'rl':row.get('rl') if row else None, 'metrics_before':comparison.get('report') if comparison else None,'metrics_after':row.get('report') if row else None,
                    'tool_requests':proposal.get('tool_requests',[]) or (row.get('tool_requests',[]) if row else []),
                    'prompt_diff':''.join(difflib.unified_diff(before['prompt'].splitlines(True),frozen['prompt'].splitlines(True),fromfile='incumbent prompt',tofile='candidate prompt')),
                    'document_diffs':{path:''.join(difflib.unified_diff(before_documents[path].splitlines(True),text.splitlines(True),fromfile='incumbent '+path,tofile='candidate '+path)) for path,text in after_documents.items() if text!=before_documents.get(path)},
                    'tools_before':before['tools'],'tools_after':frozen['tools'],
                    'parameters_before':before['target'].get('parameters',{}),'parameters_after':frozen['target'].get('parameters',{})}
        if route == '/api/fight-summary':
            groups={}
            for path in sorted((trial/'evaluations').glob('*/records/*.json')):
                record=read_json(path)
                if value('session') and record['session']!=value('session'): continue
                panel=path.parent.parent.name.split('-',1)[0]
                import re
                match=re.fullmatch(r'target-r(\d+)-g(\d+)',record['session'])
                replicate,round_number=(int(match[1])+1,int(match[2])+1) if match else (None,None)
                key=(panel,replicate,round_number,record['opponent'])
                row=groups.setdefault(key,{'panel':panel,'replicate':replicate,'round':round_number,'opponent':record['opponent'],'wins':0,'draws':0,'losses':0,'failed':0,'seeds':set()})
                row['seeds'].add(record['seed'])
                result=record['result']
                outcome='failed' if result['status']!='completed' else 'draws' if result['winner_side']==-1 else 'wins' if result['winner_side']==record['side'] else 'losses'
                row[outcome]+=1
            frozen=trial/'calibration.json'
            config=read_json(frozen)['config'] if frozen.exists() else saved_config(directory)
            return {'opponents':config['opponents'],'rows':[{**row,'seeds':sorted(row['seeds'])} for row in groups.values()],
                    'scoring':'Win = 1 point; draw = 0.5; loss = 0. Both starting sides are evaluated for every seed. Preparation fights are excluded.'}
        if route in {'/api/fights','/api/fight'}:
            fights=[]
            for path in sorted((trial/'evaluations').glob('*/records/*.json')):
                record=read_json(path)
                if value('session') and record['session'] != value('session'): continue
                panel=path.parent.parent.name.split('-',1)[0]
                fights.append({'path':record['artifact_dir'],'panel':panel,**{k:record[k] for k in ('opponent','side','seed','result')}})
            if route=='/api/fights': return fights
            match=next((m for m in fights if m['path']==value('path')),None)
            if not match: raise ArenaError('Unknown fight')
            outcome=read_json(local_path(trial,match['path'])/'outcome.json')
            from .replay import describe
            return {'match':match,'team_metrics':outcome.get('team_metrics'),
                    'events':describe(outcome.get('fight',{}))['events'], 'logs':outcome.get('logs')}
        if route == '/api/diagnostics':
            return [read_json(path) for path in sorted((trial/'diagnostics').glob('*.json'))]
        if route == '/api/judge':
            return [read_json(path) | {'session':path.stem} for path in sorted((trial/'judge').glob('*.json'))]
        if route == '/api/files':
            return [{'path':p.relative_to(trial).as_posix(), 'bytes':p.stat().st_size} for p in sorted(trial.rglob('*'))
                    if p.is_file() and not p.is_symlink() and p.name not in {'journal.sqlite','journal.sqlite-wal','journal.sqlite-shm'}]
        if route == '/api/file':
            path = local_path(trial,value('path'))
            with path.open('rb') as stream: content = stream.read(1000001)
            return {'content':content[:1000000].decode('utf-8',errors='replace'), 'truncated':len(content)>1000000}
        db = sqlite3.connect(local_path(trial,'journal.sqlite').as_uri()+'?mode=ro',uri=True)
        try:
            if route == '/api/sessions':
                return [{'id':sid, **{key:state.get(key) for key in ('status','calls','steps','generation','replicate','failure')}}
                        for sid,raw in db.execute('SELECT id,state FROM sessions ORDER BY id') for state in [json.loads(raw)]]
            sid = value('session')
            row = db.execute('SELECT state FROM sessions WHERE id=?',(sid,)).fetchone()
            if not row: raise ArenaError('Unknown session')
            state = json.loads(row[0])
            if route == '/api/diagnostic-evidence':
                from arena.calibration_transcript import export
                path=trial/'diagnostics'/f'{sid}.json'
                receipt=read_json(path) if path.exists() else {}
                evidence=([{'summary':receipt['summary']}] if receipt.get('evidence_source')=='summary' and receipt.get('summary') else export(state)['readable_reasoning'])
                return {'session':sid,'evidence_source':receipt.get('evidence_source'),'evidence':evidence,'input_wrapping':'Each reasoning/summary item is passed as {reasoning_or_summary: item}; questions are separate. Message indices are export annotations.',
                        'questions':receipt.get('questions'),'observations':receipt.get('observations',[]),'aggregation':receipt.get('aggregation'),
                        'measured_facts':{'final_compilation':state.get('validity'),'model_calls':state.get('calls'),
                                          'note':'Compilation is a measured engine result. It was not included in reasoning-only Laya input. A valid final script does not establish whether earlier attempts failed.'}}
            if route == '/api/export-conversation':
                from arena.calibration_transcript import export
                return export(state) | {'study':directory.name,'trial':value('trial'),'session':sid}
            if route == '/api/live-response':
                from arena.budget_context import progress
                snapshot=trial/'sessions'/sid/'live-response.json'
                live=read_json(snapshot) if snapshot.exists() else None
                if live and live.get('call') != state.get('calls'): live=None
                config=saved_config(directory)
                model=config.get('analyst') if sid.startswith('analyst') else config['target']
                return {'streaming_supported':bool(model and model['provider'] in {'openai','openai-compatible'} and config.get('stream_responses',True)),
                        'status':state['status'],'in_flight':state.get('in_flight',False),
                        'live':live if state.get('in_flight') or (live and live.get('phase')=='interrupted') else None,
                        'budget':progress(state,config['budget_per_session'])}
            if route == '/api/tool-exchange':
                from .tool_exchange import inspect
                from .data import history_writes
                index=int(value('index'))
                if not 0<=index<len(state['history']): raise ArenaError('Message not found')
                result=inspect(state['history'],index,list(history_writes(state['history'][:index+1])))
                if result is None: raise ArenaError('No recorded file exchange')
                return result
            if route == '/api/event':
                row=db.execute('SELECT payload FROM events WHERE session=? AND id=?',(sid,int(value('id')))).fetchone()
                if not row: raise ArenaError('Unknown event')
                reference=json.loads(row[0]);path=local_path(trial,reference['artifact'])
                if file_hash(path) != reference['sha256']: raise ArenaError('Journal artifact changed')
                return read_json(path)
            if route == '/api/conversation':
                history = state['history']
                start = max((i for i,m in enumerate(history) if m['role']=='user' and m.get('generation')==state['generation']),default=0)
                offset = max(0,int(value('offset',str(max(start,len(history)-25) if value('tail')=='1' else start))))
                page = []
                for index in range(offset,min(len(history),offset+25)):
                    message = history[index]
                    descriptors = blocks(message) if message['role'] in {'assistant','tool'} else [{'kind':message['role'], 'label':message['role'].title()+' prompt', 'value':message}]
                    from .tool_exchange import summary
                    page.append({'file_exchange':summary(history,index) if message['role']=='tool' else None, 'index':index,'role':message['role'], 'time':state.get('message_times',[])[index] if index<len(state.get('message_times',[])) else None,
                                 'blocks':[{k:v for k,v in b.items() if k!='value'} for b in descriptors]})
                return {'messages':page,'offset':offset,'next':offset+25 if offset+25<len(history) else None,'total':len(history),'round_start':start}
            if route == '/api/message':
                index = int(value('index'))
                message = state['history'][index]
                descriptors = blocks(message) if message['role'] in {'assistant','tool'} else [{'value':message}]
                return descriptors[int(value('block'))]['value']
            if route == '/api/events':
                offset = max(0,int(value('offset','0')))
                return [{'id':index,'kind':kind,'reference':json.loads(raw)} for index,kind,raw in db.execute(
                    'SELECT id,kind,payload FROM events WHERE session=? ORDER BY id LIMIT 50 OFFSET ?', (sid,offset))]
        finally: db.close()
        raise ArenaError('Unknown route')


def serve(root, port=8766, open_browser=False):
    if not 0<=port<=65535: raise ArenaError('Invalid port')
    workshop = Workshop(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,mime='application/json'):
            data = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type',mime+'; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            url = urlsplit(self.path)
            try:
                # Reject DNS rebinding and cross-origin browser access.
                host = urlsplit('http://'+self.headers.get('Host','')).hostname
                if host not in {'localhost','127.0.0.1','::1'}: raise ArenaError('Loopback host required')
                if url.path in {'/','/calibration.js','/calibration.css','/favicon.png'}:
                    name = 'calibration.html' if url.path=='/' else url.path[1:]
                    mime = 'image/png' if name.endswith('.png') else 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                    self.send(200,(STATIC/name).read_bytes(),mime)
                else: self.send(200,workshop.get(url.path,parse_qs(url.query)))
            except (ArenaError,OSError,ValueError,KeyError,IndexError,TypeError,sqlite3.Error) as error:
                self.send(400,{'error':str(error)})
        def do_POST(self):
            try:
                origin = self.headers.get('Origin')
                if origin and origin != 'http://'+self.headers.get('Host',''): raise ArenaError('Cross-origin request denied')
                if self.headers.get('X-Arena-Token') != workshop.token: raise ArenaError('Invalid request token')
                size = int(self.headers.get('Content-Length','0'))
                if not 0<size<=2000000: raise ArenaError('Invalid request size')
                data = json.loads(self.rfile.read(size))
                if self.path=='/api/start': result=workshop.start(data['config'],data.get('automatic',False),keys=data.get('keys'))
                elif self.path=='/api/resume':
                    directory=local_path(workshop.root,data['id'])
                    result=workshop.start(saved_config(directory),read_json(directory/'study.json').get('automatic',False) if (directory/'study.json').exists() else data.get('automatic',False),data['id'],data.get('keys'))
                elif self.path=='/api/stop': result=workshop.stop(data['id'])
                else: raise ArenaError('Unknown route')
                self.send(200,result)
            except (ArenaError,OSError,ValueError,KeyError,TypeError) as error: self.send(400,{'error':str(error)})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print('Calibration workshop: '+url,flush=True)
    if open_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        for identifier in list(workshop.processes): workshop.stop(identifier)
        server.server_close()
