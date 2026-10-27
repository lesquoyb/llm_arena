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


def prompt_blocks(message):
    if message.get('role')=='user' and isinstance(message.get('scenario'),dict) and isinstance(message.get('briefing'),dict):
        from arena.user_briefing import render
        from arena.model_content import visible
        return [{'kind':'user','label':'Gameplay briefing sent to model' if message.get('context_format')=='briefing-v1' else 'Gameplay briefing (readable view; original request retained)', 'value':render(visible(message))}]
    return [{'kind':message['role'],'label':message['role'].title()+' prompt','value':message}]


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
        self.usage_cache = {}

    def usage(self,directory):
        from arena.calibration import accounting
        paths=[path for db in directory.glob('**/journal.sqlite') for path in (db,db.with_name(db.name+'-wal')) if path.exists()]
        signature=[]
        for path in sorted(paths):
            try:
                info=path.stat();signature.append((str(path),info.st_mtime_ns,info.st_size))
            except FileNotFoundError: pass
        signature=tuple(signature)
        with self.lock:
            previous=self.usage_cache.get(str(directory))
        if previous and previous[0]==signature: return previous[1]
        result=accounting(directory)
        with self.lock: self.usage_cache[str(directory)]=(signature,result)
        return result

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
                         'accounting':self.usage(directory), 'error':state.get('error'), 'automatic':state.get('automatic', False)})
        return rows

    def start(self, config, automatic, identifier=None, keys=None, origin=None):
        if type(automatic) is not bool: raise ArenaError("Workflow must be a boolean")
        config = validate(config)
        if origin is not None:
            if identifier is not None or not isinstance(origin,dict) or set(origin)!={'study','candidate'} or type(origin['candidate']) is not int or origin['candidate']<1:
                raise ArenaError('Invalid source calibration reference')
            source=local_path(self.root,origin['study'])/'trials'/f"{origin['candidate']-1:03}"
            if not (source/'calibration.json').is_file(): raise ArenaError('Source candidate is not available')
        if automatic and config['max_rounds'] is None:
            raise ArenaError('Automatic candidate selection needs finite rounds; choose manual prompt editing to stop rounds manually')
        if keys is not None and (not isinstance(keys,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in keys.items())):
            raise ArenaError('Credentials must map model IDs to key strings')
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ArenaError('A calibration is running; stop it before starting another')
            from arena.calibration_models import effective_analyst
            analyst=effective_analyst(config,local_path(self.root,identifier)) if identifier else config.get('analyst')
            if config['target']['provider'] != 'mock' or (automatic and (analyst or {}).get('provider','mock') != 'mock'):
                if not config['spending']['allow_paid_calls']:
                    raise ArenaError('Activate API calls explicitly in the spending settings')
            identifier = identifier or time.strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:6]
            directory = local_path(self.root, identifier)
            if identifier in self.processes and self.processes[identifier].poll() is None:
                raise ArenaError('Study is already running')
            directory.mkdir(parents=True, exist_ok=True)
            if (directory/'study.json').exists():
                work=self.active_work(directory,read_json(directory/'study.json'))
                if work.get('requires_reconciliation'):
                    raise ArenaError('Resume cannot resend this interrupted request until it is resolved. Use "Resolve interrupted request & resume"; for a confirmed free API call, record 0 and a note.')
            if (directory/'input.json').exists() and read_json(directory/'input.json') != config:
                raise ArenaError('Resume uses the exact frozen configuration; fork to edit')
            write_json(directory/'input.json', config)
            if origin is not None: write_json(directory/'origin.json',origin)
            env = os.environ.copy()
            for model in [config['target'], effective_analyst(config,directory)]:
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

    def accept_proposal(self,identifier):
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ArenaError('Stop the study before accepting a blocked proposal')
            directory=local_path(self.root,identifier);state=read_json(directory/'study.json')
            index=state.get('active_proposal',0)
            if index<=state.get('active_trial',0): raise ArenaError('No pending prompt proposal')
            folder=directory/'proposals'/f'{index:03}'
            if (folder/'proposal.json').exists(): raise ArenaError('Proposal already frozen')
            guard=read_json(folder/'guard.json')
            if guard.get('status') not in {'rejected','needs_review'}: raise ArenaError('No rejected proposal check to override')
            draft=folder/'proposal-draft.json'
            # Scope the decision to this exact proposal and this exact guard result.
            write_json(folder/'guard-override.json',{'draft_sha256':file_hash(draft),'guard_identity':guard['identity'],'at':time.time(),'reason':'User accepted the saved proposal despite the experimental semantic check.'})
            return {'accepted':True,'candidate':index+1}

    def recover_target(self, identifier, instructions='', reconciliation=None):
        from arena.experiment import Journal
        from arena.recovery import needs_reconciliation,reconcile
        if not isinstance(instructions,str) or len(instructions)>100000:
            raise ArenaError('Instructions must be text, maximum 100000 characters')
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ArenaError('Stop the study before recovering its target conversation')
            directory=local_path(self.root,identifier)
            manifest=read_json(directory/'study.json')
            index=manifest.get('active_trial',0)
            folder=directory/'trials'/f'{index:03}'
            report=read_json(folder/'report.json') if (folder/'report.json').exists() else {}
            if report.get('status') == 'completed' or index < len(manifest.get('trials', [])):
                raise ArenaError('This observation has already been evaluated. Resume the optimization to let the analyst use its result, or start a new study; completed observations cannot be reopened.')
            journal=Journal(folder)
            try:
                sid=report.get('session')
                if not sid:
                    candidates=[sid for sid,state in journal.states().items() if not state.get('submission')]
                    if len(candidates)!=1: raise ArenaError('Cannot identify the unfinished target conversation')
                    sid=candidates[0]
                state=journal.state(sid)
                if not state or state.get('submission'): raise ArenaError('No unfinished target conversation')
                if state.get('pending') and instructions.strip():
                    raise ArenaError('Pending tools must finish before new instructions can be added. Continue without instructions first.')
                if needs_reconciliation(state):
                    if not isinstance(reconciliation,dict):
                        raise ArenaError('This response needs billing reconciliation. Enter its confirmed additional cost and a note before continuing.')
                    state=reconcile(journal,sid,reconciliation.get('cost_usd'),reconciliation.get('note'))
                if state['status'] not in {'running','no_submission','generation_failed','provider_unavailable'}:
                    raise ArenaError('This conversation cannot be continued: '+state['status'])
                state.update(status='running',submission_reminders=0,consecutive_submission_reminders=0)
                state.pop('failure',None)
                if not state.get('pending'):
                    state['history'].append({'role':'user','content':
                        'The preparation round is still open. You have not submitted a strategy. Continue from your saved workspace, fix any invalid tool arguments, analyze your LeekScript and explicitly call submit. '+instructions,
                        'human_supplied':True})
                journal.save(sid,state,'human_target_continue',{'instructions':instructions,'pending_tools_preserved':bool(state.get('pending'))})
            finally: journal.db.close()
            manifest.update(status='stopped',error='Target conversation ready. Resume to continue.')
            write_json(directory/'study.json',manifest)
            return {'session':sid,'recorded':True}

    def intervene(self, identifier, text, replacement=False):
        """Record an explicit human intervention; never overwrite provider receipts."""
        from arena.experiment import Journal
        if type(replacement) is not bool: raise ArenaError('Replacement must be a boolean')
        if not isinstance(text,str) or not text.strip() or len(text)>500000:
            raise ArenaError('Provide instructions or a corrected proposal (maximum 500000 characters)')
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ArenaError('Stop the running study before intervening')
            directory=local_path(self.root,identifier)
            manifest=read_json(directory/'study.json')
            index=manifest.get('active_proposal')
            if index is None or index<=manifest.get('active_trial',0):
                raise ArenaError('No unfinished analyst proposal. Use the conversation controls for target model failures.')
            folder=directory/'proposals'/f'{index:03}'
            if (folder/'proposal.json').exists(): raise ArenaError('This proposal is already frozen')
            if replacement:
                proposal=json.loads(text)
                if not isinstance(proposal,dict): raise ArenaError('Proposal must be a JSON object')
            journal=Journal(folder)
            try:
                from arena.calibration_models import active_analyst_session
                analyst_sid=active_analyst_session(folder)
                state=journal.state(analyst_sid)
                if not state: raise ArenaError('No analyst conversation to recover')
                if state.get('in_flight') or state.get('status')=='needs_reconciliation':
                    raise ArenaError('Resolve billing reconciliation before intervening')
                state.update(status='running',repair_attempts=0,format_repair_attempts=0,pending=None)
                state.pop('failure',None)
                if replacement:
                    response={'role':'assistant','content':text,'human_supplied':True}
                    state['history'].append({'role':'user','content':'Human corrected proposal JSON:\n'+text,'human_supplied':True});state['pending']=response
                else:
                    state['history'].append({'role':'user','content':text+'\nReturn the complete corrected proposal as JSON, following the original analyst instructions.'})
                journal.save(analyst_sid,state,'human_proposal_replacement' if replacement else 'human_analyst_instruction',{'text':text})
            finally: journal.db.close()
            manifest.update(status='stopped',error='Human intervention recorded. Resume to continue.')
            write_json(directory/'study.json',manifest)
            return {'recorded':True,'candidate':index+1}

    def model_roles(self, identifier):
        from arena.calibration_models import effective_analyst
        directory=local_path(self.root,identifier);config=saved_config(directory)
        history=read_json(directory/'role-models.json').get('history',[]) if (directory/'role-models.json').exists() else []
        outstanding=[];seen=set()
        for change in history:
            for request in change.get('retired_requests',[]):
                key=(request['directory'],request['session'])
                if key in seen:continue
                seen.add(key);path=local_path(directory,request['directory'])/'journal.sqlite'
                if not path.is_file():continue
                db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
                try:row=db.execute('SELECT state FROM sessions WHERE id=?',(request['session'],)).fetchone()
                finally:db.close()
                if row:
                    from arena.recovery import needs_reconciliation
                    state=json.loads(row[0])
                    if needs_reconciliation(state):outstanding.append({**request,'reserved_usd':state.get('money_reserved','0')})
        return {'outstanding_requests':outstanding,'target':config['target'],'analyst':effective_analyst(config,directory),
                'diagnostics':config.get('diagnostics',{}),'proposal_guard':config.get('proposal_guard',{}),
                'evaluation':config.get('evaluation',{}),
                'history':history}

    def set_analyst_model(self, identifier, participant):
        from arena.calibration_models import effective_analyst
        from arena.experiment import experiment_lock
        directory=local_path(self.root,identifier)
        with self.lock,experiment_lock(directory):
            if any(process.poll() is None for process in self.processes.values()):
                raise ArenaError('Stop the optimization before changing its analyst')
            directory=local_path(self.root,identifier)
            config=saved_config(directory)
            if read_json(directory/'study.json').get('status')=='completed':
                raise ArenaError('This optimization is complete. Start a new calibration from a saved candidate to change models.')
            model=next((row for row in self.store.catalog() if row['id']==participant),None)
            if not model or model['provider']=='mock': raise ArenaError('Choose a saved API model for the analyst')
            self.store.validate_model(model)
            if not config['spending']['allow_paid_calls']:
                raise ArenaError('API requests are disabled in this study. Start a new calibration with API requests enabled.')
            previous=effective_analyst(config,directory)
            path=directory/'role-models.json';saved=read_json(path) if path.exists() else {}
            from arena.calibration_models import replace_active_analyst_sessions
            retired=replace_active_analyst_sessions(directory,config,model)
            history=saved.get('history',[])+[{'retired_requests':retired,'role':'analyst','at':time.time(),'previous':previous,'model':model,'scope':'Future analyst and trajectory-summary requests; completed results are preserved.'}]
            write_json(path,{'analyst':model,'history':history})
            manifest=read_json(directory/'study.json')
            manifest.update(status='stopped',error='Analyst changed to '+model['id']+'. Resume optimization to continue. Earlier unknown requests and reservations are preserved.')
            write_json(directory/'study.json',manifest)
            return {'saved':True,'model':model['id'],'retired_requests':retired}

    def reconcile_active(self, identifier, cost, note, trial=None, session=None):
        from arena.experiment import Journal
        from arena.recovery import reconcile
        with self.lock:
            if any(process.poll() is None for process in self.processes.values()):
                raise ArenaError('Stop the running optimization before resolving an interrupted request')
            directory=local_path(self.root,identifier)
            manifest=read_json(directory/'study.json')
            work=self.active_work(directory,manifest)
            folder=local_path(directory,trial or work['directory'])
            if not (folder/'journal.sqlite').is_file(): raise ArenaError('No recorded conversation to resolve')
            journal=Journal(folder)
            try:
                candidates=[sid for sid,state in journal.states().items() if (session is None or sid==session) and (state.get('in_flight') or state.get('status')=='needs_reconciliation')]
                if len(candidates)!=1: raise ArenaError('Cannot identify one interrupted request in the active candidate')
                sid=candidates[0]
                reconcile(journal,sid,cost,note)
            finally:journal.db.close()
            manifest.update(status='stopped',error='Interrupted request reconciled; resume to continue the saved optimization.')
            write_json(directory/'study.json',manifest)
            return {'session':sid,'reconciled':True}

    def set_analyst_input_limit(self, identifier, limit):
        from arena.core import integer
        if limit is not None: integer(limit,1,100_000_000,'analyst input admission limit')
        with self.lock:
            if any(process.poll() is None for process in self.processes.values()):
                raise ArenaError('Stop the running optimization before changing the analyst input cap')
            directory=local_path(self.root,identifier)
            manifest=read_json(directory/'study.json')
            work=self.active_work(directory,manifest)
            if work['kind']!='analyst' or work.get('session_status')!='budget_exhausted':
                raise ArenaError('No analyst budget pause to resolve')
            stop=work.get('budget_stop') or {}
            legacy=work.get('message','').startswith('Request exceeds conservative UTF-8 input admission bound')
            if stop.get('code')!='input_admission' and not legacy:
                raise ArenaError('This pause is not an analyst input admission limit')
            analyst=saved_config(directory).get('analyst')
            if not analyst: raise ArenaError('No analyst configured')
            policy={'analyst_sha256':digest(analyst),'max_input_tokens_per_call':limit,'at':time.time(),
                    'reason':'User changed the analyst input admission cap for this study. Target limits and the shared spending ceiling remain unchanged.'}
            write_json(directory/'analyst-runtime.json',policy)
            return {'saved':True}

    def active_work(self,directory,state):
        proposal=state.get('active_proposal',0)>state.get('active_trial',0)
        index=state.get('active_proposal',0) if proposal else state.get('active_trial',0)
        folder=directory/('proposals' if proposal else 'trials')/f'{index:03}'
        result={'kind':'analyst' if proposal else 'target','candidate':index+1,'directory':folder.relative_to(directory).as_posix(),'message':state.get('error','')}
        guard=folder/'guard.json'
        if proposal and guard.exists():
            result['guard_status']=read_json(guard).get('status')
            result['guard_override_available']=result['guard_status']=='rejected' and (folder/'proposal-draft.json').exists() and not (folder/'proposal.json').exists()
        dbpath=folder/'journal.sqlite'
        if dbpath.exists():
            db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
            try:
                from arena.calibration_models import active_analyst_session
                condition=' WHERE id=?' if proposal else ''
                params=(active_analyst_session(folder),) if proposal else ()
                rows=db.execute("SELECT json_extract(state,'$.status','$.proposal_phase','$.proposal_error','$.in_flight','$.failure.message','$.budget_stop') FROM sessions"+condition+" ORDER BY id",params).fetchall()
                for (raw,) in rows:
                    status,phase,error,in_flight,failure,budget_stop=json.loads(raw)
                    if proposal or status not in {'submitted','budget_exhausted'}:
                        result.update(session_status=status,phase=phase,proposal_error=error,budget_stop=budget_stop,requires_reconciliation=bool(in_flight or status=='needs_reconciliation'))
                        if error or failure: result['message']=error or failure
                        if budget_stop and status=='budget_exhausted': result['message']=budget_stop['message']
            finally: db.close()
        return result

    def get(self, route, query):
        value = lambda key, default='': query.get(key,[default])[0]
        if route == '/api/bootstrap':
            from arena.feedback import available_tools
            from arena.presets import simple_scenario, participant_scenario, dream_team_scenario
            scenarios={'simple':simple_scenario(),'llm-team':participant_scenario()}
            try: scenarios['dream-team']=dream_team_scenario()
            except (ArenaError,OSError): pass
            current_defaults=defaults()
            return {'token':self.token,'config':current_defaults,'prompt_source':{'path':'prompts/g0.md','sha256':digest(current_defaults['prompt'])},'participants':self.store.participants(),
                    'reference_documents':original_documents(),
                    'tools':available_tools({'calibration':{'tools':[t['name'] for t in TOOLS]}}),'scenarios':scenarios}
        if route == '/api/studies': return self.listing()
        directory = local_path(self.root,value('study'))
        if route == '/api/study':
            proposal_paths={p.parent:(p.parent/'proposal.json' if (p.parent/'proposal.json').exists() else p) for pattern in ('proposals/*/proposal.json','proposals/*/proposal-draft.json') for p in directory.glob(pattern)}
            return {'origin':read_json(directory/'origin.json') if (directory/'origin.json').exists() else None,'model_roles':self.model_roles(directory.name),'runtime_status':next((row['status'] for row in self.listing() if row['id']==directory.name), 'stopped'), 'config':saved_config(directory), 'state':read_json(directory/'study.json') if (directory/'study.json').exists() else {},'accounting':self.usage(directory),'active_work':self.active_work(directory,read_json(directory/'study.json') if (directory/'study.json').exists() else {}),
                    'progress': [{'trial': p.parent.name, 'value':read_json(p)} for p in directory.glob('trials/*/progress.json')],
                    'active_reports':{p.parent.relative_to(directory).as_posix():read_json(p) for p in directory.glob('trials/*/report.json')},
                    'diagnostic_revision':[(p.relative_to(directory).as_posix(),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted(directory.glob('trials/*/diagnostics/*.json'))],
                    'trial_directories':[p.parent.relative_to(directory).as_posix() for p in sorted(directory.glob('trials/*/journal.sqlite'),key=lambda p:int(p.parent.name))],
                    'proposal_directories':[p.parent.relative_to(directory).as_posix() for p in sorted(directory.glob('proposals/*/journal.sqlite'),key=lambda p:int(p.parent.name))],
                    'proposals':[{'directory':p.parent.relative_to(directory).as_posix(),'candidate':int(p.parent.name)+1,
                                  'rationale':read_json(p).get('rationale',''),'guard_status':read_json(p.parent/'guard.json').get('status') if (p.parent/'guard.json').exists() else None} for p in sorted(proposal_paths.values(),key=lambda p:int(p.parent.name))]}
        if route == '/api/prompt-history':
            state=read_json(directory/'study.json') if (directory/'study.json').exists() else {}
            paths={}
            for path in sorted(directory.glob('proposals/*/proposal-draft.json'))+sorted(directory.glob('proposals/*/proposal.json'))+sorted(directory.glob('trials/*/calibration.json')):
                paths[int(path.parent.name)]=path
            rows=[]
            for index,path in sorted(paths.items()):
                row=next((r for r in state.get('trials',[]) if r['directory']==f'trials/{index:03}'),None)
                report=(row or {}).get('report',{})
                guard_path=directory/'proposals'/f'{index:03}'/'guard.json'
                rows.append({'candidate':index+1,'directory':path.parent.relative_to(directory).as_posix(),
                             'source_candidate':row['parent']+1 if row and row.get('parent') is not None else (state.get('active_parent') or 0)+1 if not row and index else None,
                             'status':'No change proposed' if path.name in {'proposal.json','proposal-draft.json'} and read_json(path).get('no_change') else 'Current best' if state.get('incumbent')==index else 'Initial baseline' if index==0 else 'Selected earlier' if row and row['accepted'] else 'Not selected' if row else 'Blocked proposal' if guard_path.exists() and read_json(guard_path)['status'] in {'rejected','unavailable'} else 'Untested proposal',
                             'score':report.get('validation_score'),'tokens':report.get('tokens'),'cost_usd':report.get('cost_usd')})
            return {'study':directory.name,'name':saved_config(directory)['name'],'versions':rows}
        if route == '/api/reusable-config':
            import io,zipfile
            data=self.get('/api/export-material',query)
            with zipfile.ZipFile(io.BytesIO(data)) as archive: return json.loads(archive.read('calibration.json'))
        if route == '/api/prompt-diff':
            after=self.get('/api/proposal' if value('trial').startswith('proposals/') else '/api/candidate',query)
            base=value('base')
            before=self.get('/api/proposal' if base.startswith('proposals/') else '/api/candidate',{**query,'trial':[base]}) if base else after
            import difflib
            after_config=self.get('/api/reusable-config',query)
            before_config=self.get('/api/reusable-config',{**query,'trial':[base]}) if base else after_config
            files=['system prompt',*sorted(set(after_config['reference_documents'])|set(before_config['reference_documents']))]
            name=value('file','system prompt')
            if name not in files: raise ArenaError('Unknown learning material file')
            old=before_config['prompt'] if name=='system prompt' else before_config['reference_documents'].get(name,'')
            new=after_config['prompt'] if name=='system prompt' else after_config['reference_documents'].get(name,'')
            return {'before':old,'after':new,'files':files,'diff':''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='candidate '+str(before['candidate'])+'/'+name,tofile='candidate '+str(after['candidate'])+'/'+name)),
                    'candidate':after['candidate'],'rationale':after['rationale']}
        if route == '/api/tool-requests':
            return [{'candidate':int(path.parent.name)+1, 'requests':read_json(path).get('tool_requests',[])}
                    for path in sorted(directory.glob('proposals/*/proposal.json'),key=lambda p:int(p.parent.name))]
        if route == '/api/log':
            path = directory/'worker.log'
            with path.open('rb') as stream:
                stream.seek(max(0,path.stat().st_size-128000))
                return {'content':stream.read().decode('utf-8',errors='replace')}
        trial = local_path(directory,value('trial'))
        if route == '/api/proposal-checks':
            folder=trial if value('trial').startswith('proposals/') else directory/'proposals'/trial.name
            checks={}
            for path in sorted((folder/'guards').glob('*.json')):
                receipt=read_json(path);checks[receipt.get('identity',path.name)]={'attempt':None,'receipt':receipt}
            for path in sorted((folder/'attempts').glob('*-guard.json')):
                receipt=read_json(path);checks.pop(receipt.get('identity'),None)
                checks[path.name]={'attempt':int(path.name.split('-')[0]),'receipt':receipt}
            current=read_json(folder/'guard.json') if (folder/'guard.json').exists() else {}
            if current and not any(row['receipt'].get('identity')==current.get('identity') for row in checks.values()):
                checks['current']={'attempt':None,'receipt':current}
            return {'current_identity':current.get('identity'),'checks':sorted(checks.values(),key=lambda row:(row['attempt'] is not None,row['attempt'] or 0)),
                    'note':'Inputs and questions are recorded exactly as passed to predict_long. response contains the complete returned library object when available. Older receipts retain answers and usage only; missing output cannot be reconstructed. Laya returns structured scores, not a hidden reasoning transcript.'}
        if route == '/api/export-material':
            from arena.calibration_export import bundle
            review=self.get('/api/proposal' if value('trial').startswith('proposals/') else '/api/candidate',query)
            return bundle(directory,review)
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
                proposal_path=trial/'proposal.json' if (trial/'proposal.json').exists() else trial/'proposal-draft.json'
                proposal=read_json(proposal_path) if proposal_path.exists() else {}
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
            guard_result=read_json(guard_path) if guard_path.exists() else None
            check_blocked=bool(guard_result and guard_result.get('status') in {'rejected','unavailable'} and state['config'].get('proposal_guard',{}).get('enabled') and state['config'].get('proposal_guard',{}).get('mode','automatic')=='automatic' and not guard_path.with_name('guard-override.json').exists())
            return {'guard_override':read_json(guard_path.with_name('guard-override.json')) if guard_path.with_name('guard-override.json').exists() else None,'guard':read_json(guard_path) if guard_path.exists() else None,'guard_enabled':state['config'].get('proposal_guard',{}).get('enabled',False), 'config':frozen,'current_best':state.get('incumbent')==candidate,'comparison_candidate':comparison_index+1 if comparison_index is not None else None,'candidate':candidate+1,'baseline':candidate==0,
                    'diagnostic_candidate':(parent_index+1 if parent_index is not None else 1) if route=='/api/proposal' else candidate+1,
                    'analyst_directory':f'proposals/{candidate:03}' if (directory/'proposals'/f'{candidate:03}'/'journal.sqlite').is_file() else None,
                    'decision_reason':proposal['rationale'] if proposal.get('no_change') else ('Not evaluated: the proposal check returned '+read_json(guard_path)['status']+'.') if not row and check_blocked else decision_reason(row,comparison,state['config'],candidate),
                    'no_change':proposal.get('no_change',False),'decision':'No change proposed' if proposal.get('no_change') else 'Baseline' if candidate==0 else 'Kept' if row and row['accepted'] else 'Rejected' if row else 'Blocked by proposal check' if check_blocked else 'Pending evaluation',
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
        journal_path=local_path(trial,'journal.sqlite')
        if not journal_path.is_file():
            if route=='/api/sessions': return []
            raise ArenaError('No conversation has been recorded for this candidate yet. The initial baseline has no analyst proposal.')
        db = sqlite3.connect(journal_path.as_uri()+'?mode=ro',uri=True)
        try:
            if route == '/api/sessions':
                from arena.call_counts import completed_calls
                from arena.calibration_models import active_analyst_session
                return [{'id':sid, **{key:state.get(key) for key in ('status','steps','generation','replicate','failure')},
                         'calls':completed_calls(state,db,sid),'request_attempts':state.get('calls',0),
                         'model_label':(state.get('model_descriptor') or {}).get('model',state.get('model','')),
                         'active':not sid.startswith('analyst') or sid==active_analyst_session(trial),
                         'supersedes':state.get('supersedes_analyst_session')}
                        for sid,raw in db.execute('SELECT id,state FROM sessions ORDER BY id') for state in [json.loads(raw)]]
            sid = value('session')
            row = db.execute('SELECT state FROM sessions WHERE id=?',(sid,)).fetchone()
            if not row: raise ArenaError('Unknown session')
            state = json.loads(row[0])
            from arena.call_counts import hydrate_calls
            hydrate_calls(state,db,sid)
            if route == '/api/diagnostic-evidence':
                from arena.calibration_transcript import export
                path=trial/'diagnostics'/f'{sid}.json'
                receipt=read_json(path) if path.exists() else {}
                evidence=([{'summary':receipt['summary']}] if receipt.get('evidence_source')=='summary' and receipt.get('summary') else export(state)['readable_reasoning'])
                return {'session':sid,'evidence_source':receipt.get('evidence_source'),'evidence':evidence,'input_wrapping':'Each reasoning/summary item is passed as {reasoning_or_summary: item}; questions are separate. Message indices are export annotations.',
                        'questions':receipt.get('questions'),'observations':receipt.get('observations',[]),'aggregation':receipt.get('aggregation'),
                        'measured_facts':{'final_compilation':state.get('validity'),'model_calls':state['completed_calls'],'request_attempts':state.get('calls',0),
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
                        'status':state['status'],'in_flight':state.get('in_flight',False),'role':'analyst' if sid.startswith('analyst') else 'target',
                        'calls':state['completed_calls'],'request_attempts':state.get('calls',0),'repair_attempts':state.get('repair_attempts',0),'proposal_phase':state.get('proposal_phase'),'proposal_error':state.get('proposal_error'),'failure':state.get('failure'),'model_descriptor':state.get('model_descriptor') or model,
                        'live':live if state.get('in_flight') or (live and live.get('phase')=='interrupted') else None,
                        'budget':None if sid.startswith('analyst') else progress(state,config['budget_per_session'])}
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
                    descriptors = blocks(message) if message['role'] in {'assistant','tool'} else prompt_blocks(message)
                    from .tool_exchange import summary
                    page.append({'inherited_from_session':message.get('inherited_from_session'),'file_exchange':summary(history,index) if message['role']=='tool' else None, 'index':index,'role':message['role'], 'time':state.get('message_times',[])[index] if index<len(state.get('message_times',[])) else None,
                                 'blocks':[{k:v for k,v in b.items() if k!='value'} for b in descriptors]})
                return {'messages':page,'offset':offset,'next':offset+25 if offset+25<len(history) else None,'total':len(history),'round_start':start}
            if route == '/api/message':
                index = int(value('index'))
                message = state['history'][index]
                descriptors = blocks(message) if message['role'] in {'assistant','tool'} else prompt_blocks(message)
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
                if url.path in {'/','/prompt-history','/calibration-history.js','/calibration.js','/calibration.css','/favicon.png'}:
                    name = 'calibration.html' if url.path=='/' else 'calibration-history.html' if url.path=='/prompt-history' else url.path[1:]
                    mime = 'image/png' if name.endswith('.png') else 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                    self.send(200,(STATIC/name).read_bytes(),mime)
                else: self.send(200,workshop.get(url.path,parse_qs(url.query)),'application/zip' if url.path=='/api/export-material' else 'application/json')
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
                if self.path=='/api/start': result=workshop.start(data['config'],data.get('automatic',False),keys=data.get('keys'),origin=data.get('origin'))
                elif self.path=='/api/test-model':
                    from .model_probe import probe_model
                    if data.get('spec') is not None:
                        model=data['spec']
                    else:
                        roles=workshop.model_roles(data['id'])
                        if data.get('role') not in {'target','analyst'}: raise ArenaError('Choose target or analyst')
                        model=roles[data['role']]
                    if not isinstance(model,dict): raise ArenaError('No model assigned to this role')
                    result=probe_model(workshop.store,model,data.get('mode','text'),data.get('secret') or (data.get('keys') or {}).get(model.get('id')))
                elif self.path=='/api/analyst-model': result=workshop.set_analyst_model(data['id'],data['participant'])
                elif self.path=='/api/reconcile-active':
                    result=workshop.reconcile_active(data['id'],data.get('cost_usd'),data.get('note'),data.get('trial'),data.get('session'))
                    directory=local_path(workshop.root,data['id'])
                    try:
                        workshop.start(saved_config(directory),read_json(directory/'study.json').get('automatic',False),data['id'],data.get('keys'))
                    except (ArenaError,OSError,ValueError) as exc:
                        raise ArenaError('Request reconciled, but the worker could not restart: '+str(exc)) from exc
                    result['started']=True
                elif self.path=='/api/analyst-input-limit':
                    result=workshop.set_analyst_input_limit(data['id'],data.get('limit'))
                    directory=local_path(workshop.root,data['id'])
                    try:
                        workshop.start(saved_config(directory),read_json(directory/'study.json').get('automatic',False),data['id'],data.get('keys'))
                    except (ArenaError,OSError,ValueError) as exc:
                        raise ArenaError('Analyst input cap saved, but the worker could not restart: '+str(exc)) from exc
                    result['started']=True
                elif self.path=='/api/accept-proposal': result=workshop.accept_proposal(data['id'])
                elif self.path=='/api/recover-target':
                    result=workshop.recover_target(data['id'],data.get('instructions',''),data.get('reconciliation'))
                    if data.get('resume'):
                        directory=local_path(workshop.root,data['id'])
                        try:
                            workshop.start(saved_config(directory),read_json(directory/'study.json').get('automatic',False),data['id'],data.get('keys'))
                        except (ArenaError,OSError,ValueError) as exc:
                            raise ArenaError('Instructions saved, but the worker could not restart: '+str(exc)) from exc
                        result['started']=True
                elif self.path=='/api/intervene': result=workshop.intervene(data['id'],data['text'],data.get('replacement',False))
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
