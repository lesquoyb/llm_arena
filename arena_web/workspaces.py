"""Workspace membership and read-only campaign summaries, outside frozen runs."""
from collections import defaultdict
from decimal import Decimal
from functools import cache
import time
from uuid import uuid4

from arena.core import ArenaError, digest, write_json


class Workspaces:
    def workspace_index(self):
        return self.json(self.state/'workspaces.json', {'workspaces':[], 'runs':{}, 'drafts':{}})

    def workspace(self, identifier):
        row=next((row for row in self.workspace_index()['workspaces'] if row['id']==identifier),None)
        if row is None: raise ArenaError('Workspace not found')
        return row

    def save_workspace(self, name, identifier=None, description=''):
        if not isinstance(name,str) or not name.strip() or len(name.strip())>100:
            raise ArenaError('Workspace name must contain 1 to 100 characters')
        if not isinstance(description,str) or len(description)>2000:
            raise ArenaError('Workspace description must contain at most 2,000 characters')
        with self.lock:
            index=self.workspace_index()
            current=self.workspace(identifier) if identifier else {'id':uuid4().hex[:12], 'created_at':time.time()}
            if any(row['name'].casefold()==name.strip().casefold() and row['id']!=current['id'] for row in index['workspaces']):
                raise ArenaError('A workspace with this name already exists')
            row={**current,'name':name.strip(),'description':description.strip()}
            index['workspaces']=[r for r in index['workspaces'] if r['id']!=row['id']]+[row]
            write_json(self.state/'workspaces.json',index)
            return row

    def delete_workspace(self, identifier):
        with self.lock:
            self.workspace(identifier)
            index=self.workspace_index()
            index['workspaces']=[row for row in index['workspaces'] if row['id']!=identifier]
            for kind in ('runs','drafts'):
                index[kind]={key:value for key,value in index[kind].items() if value!=identifier}
            write_json(self.state/'workspaces.json',index)
        return {'deleted':identifier}

    def assign_workspace(self, workspace, runs=None, drafts=None, replace=False):
        runs=[] if runs is None else runs
        drafts=[] if drafts is None else drafts
        for identifiers in (runs,drafts):
            if not isinstance(identifiers,list) or len(identifiers)>2000 or any(not isinstance(key,str) for key in identifiers):
                raise ArenaError('Select at most 2,000 competitions or configurations')
        with self.lock:
            if workspace is not None: self.workspace(workspace)
            if replace and workspace is None: raise ArenaError('Choose a workspace to manage its members')
            # Validate the complete operation before changing membership.
            for identifier in runs: self.run_path(identifier)
            for identifier in drafts: self.draft(identifier)
            index=self.workspace_index()
            for kind,identifiers in (('runs',runs),('drafts',drafts)):
                if replace: index[kind]={key:value for key,value in index[kind].items() if value!=workspace}
                for identifier in identifiers:
                    if workspace is None: index[kind].pop(identifier,None)
                    else: index[kind][identifier]=workspace
            write_json(self.state/'workspaces.json',index)
        return {'saved':True}

    def inherit_workspace(self, draft, run):
        # Called before worker creation; the run folder may not exist yet.
        with self.lock:
            index=self.workspace_index()
            workspace=index['drafts'].get(draft)
            if workspace:
                index['runs'][run]=workspace
                write_json(self.state/'workspaces.json',index)

    def workspace_runs(self, identifier):
        if identifier not in {'','unassigned'}: self.workspace(identifier)
        return [row for row in self.listing() if not identifier or
                (row.get('workspace_id') is None if identifier=='unassigned' else row.get('workspace_id')==identifier)]

    def workspace_summary(self, identifier):
        runs=self.workspace_runs(identifier)
        included=[r for r in runs if not r.get('archived') and not r.get('error')]
        excluded=[{'run':r['id'],'reason':'Exported copy' if r.get('archived') else r.get('error')} for r in runs if r not in included]
        totals={'competitions':len(included),'sessions':0,'submitted':0,'frozen_strategies':0,'invalid':0,'attention':0,
                'completed_matches':0,'failed_matches':0,'preparation_matches':0,
                'input_tokens':0,'output_tokens':0,'unmeasured_sessions':0,
                'known_cost_usd':Decimal(0),'reserved_usd':Decimal(0),'unresolved_sessions':0}
        resources={};groups={}
        for run in included:
            detail=self.detail(run['id']);metadata=detail['metadata']
            config=metadata.get('config',metadata.get('manifest',{}))
            models={m['id']:m for m in config.get('models',[])}
            frozen={s['id']:s for s in config.get('strategies',[])}
            totals['frozen_strategies']+=len(frozen)
            sessions={s['id']:s for s in detail['sessions']}
            @cache
            def descriptor(sid):
                state=sessions.get(sid,{})
                model=models.get(state.get('model'),{})
                if not model:
                    source=frozen.get(sid,{})
                    origin=source.get('origin',{})
                    return {'variant':origin.get('variant',source.get('model',sid)), 'provider':origin.get('provider'),
                        'model':origin.get('model'), 'parameters':origin.get('parameters',{}),
                        'source_sha256':source.get('submission',{}).get('sha256')}
                spec={k:v for k,v in model.items() if k not in {'api_key_env','pricing','id','model_size_billion'}}
                if 'strategy' in spec:
                    spec['strategy']={k:v for k,v in spec['strategy'].items() if k!='files'}
                return spec | {'variant':state['model'], 'parameters':{**model.get('parameters',{}),**state.get('provider_parameter_overrides',{})}}
            @cache
            def track(sid):
                state=sessions.get(sid)
                if state:return state.get('generation',0)+1,state.get('condition','initial')
                origin=frozen.get(sid,{}).get('origin',{})
                return origin.get('round'),origin.get('condition','frozen')
            @cache
            def participant_key(sid):
                return digest({key:value for key,value in descriptor(sid).items() if key!='source_sha256'})
            @cache
            def model_size(sid):
                state=sessions.get(sid,{})
                return self.model_size(models[state['model']]) if state.get('model') in models else frozen.get(sid,{}).get('origin',{}).get('model_size_billion')
            for sid,state in sessions.items():
                totals['sessions']+=1
                totals['submitted']+=bool(state.get('submission'))
                totals['invalid']+=state.get('validation_status')=='invalid'
                totals['attention']+=not state.get('withdrawn') and state.get('status') in {'provider_unavailable','needs_reconciliation','generation_failed','no_submission'}
                key=digest(descriptor(sid))[:16]
                resource=resources.setdefault(key,{'id':key,'name':state['model'],'model':models.get(state['model'],{}).get('model'),
                    'model_size_billion':model_size(sid),
                    'configuration':descriptor(sid),
                    'sessions':0,'submitted':0,'invalid':0,'input_tokens':0,'output_tokens':0,'unmeasured_sessions':0,
                    'known_cost_usd':Decimal(0),'reserved_usd':Decimal(0),'unresolved_sessions':0,'messages':0,'tool_calls':0,'wall_seconds':0})
                if resource['model_size_billion']!=model_size(sid):resource['model_size_billion']=None
                resource['sessions']+=1;resource['submitted']+=bool(state.get('submission'))
                resource['invalid']+=state.get('validation_status')=='invalid'
                resource['tool_calls']+=state.get('steps',0);resource['messages']+=state.get('messages',0);resource['wall_seconds']+=state.get('wall_seconds',0)
                receipt=state.get('usage_receipts') or {}
                measured=not receipt.get('missing_usage') if receipt.get('responses') else state.get('token_usage_known',False)
                for field in ('input_tokens','output_tokens'):
                    value=receipt.get(field,0) if receipt.get('responses') else state.get(field,0) if measured else 0
                    resource[field]+=value or 0;totals[field]+=value or 0
                for target in (resource,totals):
                    target['unmeasured_sessions']+=not measured
                    target['known_cost_usd']+=Decimal(state.get('cost_spent') or '0')
                    target['reserved_usd']+=Decimal(state.get('money_reserved') or '0')
                    target['unresolved_sessions']+=bool(state.get('reconciliation_required'))
            # Scores only combine the same scenario, preparation and configured pool.
            # Different opponent pools remain separate even inside one workspace.
            protocol={'participant_changes':{key:value for key,value in (detail.get('roster') or {}).items() if key in {'revision','active','withdrawn','frozen_tracks','at_round'}}, 'scenario':config.get('scenario'), 'engine':metadata.get('scientific_identity',metadata.get('engine')),
                'seeds':{k:v for k,v in config.items() if 'seed' in k},
                'budget':config.get('budget_per_session'),'parallel_requests':config.get('parallel_requests',1),'corpus':metadata.get('corpus_sha256'),
                'prompts':metadata.get('prompts_sha256',metadata.get('prompt_sha256')),
                'catalogs':metadata.get('catalogs'),
                'continuations':sorted({digest(s['continuation_identity']) for s in sessions.values() if s.get('continuation_identity')})}
            matches=self.matches(run['id'])['matches']
            panels=defaultdict(set);pools=defaultdict(set)
            for match in matches:
                if match['kind']!='training':pools[match['stage']].update(match['sides'])
                if match['kind'] not in {'evaluation','progression'}:continue
                sources=self.json(self.run_path(run['id'])/match['path']/'provenance.json',{}).get('submissions',[])
                side=match.get('candidate_side')
                opponent=sources[1-side].get('sha256') if side in (0,1) and len(sources)==2 else None
                panels[match['stage']].add(opponent or 'unknown:'+run['id'])
            stage_pools={stage:sorted([descriptor(sid) | {'replicate':sessions.get(sid,{}).get('replicate'),
                'round':sessions.get(sid,{}).get('generation',0),'condition':sessions.get(sid,{}).get('condition','frozen')}
                for sid in sides],key=digest) for stage,sides in pools.items()}
            group_keys={}
            for match in matches:
                result=match['result'];done=result.get('status')=='completed'
                if match['kind']=='training':
                    totals['preparation_matches']+=done
                    continue
                totals['completed_matches']+=done;totals['failed_matches']+=not done
                if match.get('mirror'):continue
                candidates=[(side,sid) for side,sid in enumerate(match['sides']) if sid in sessions or sid in frozen]
                if match['kind'] in {'evaluation','progression'}: candidates=[(side,sid) for side,sid in candidates if sid==match.get('candidate')]
                # Missing immutable panel provenance cannot support cross-run pooling.
                reference=sorted(panels[match['stage']]) if match['kind'] in {'evaluation','progression'} else None
                stage_key=(match['kind'],match['stage'])
                if stage_key not in group_keys:
                    group_keys[stage_key]=digest({'protocol':protocol,'pool':stage_pools[match['stage']],
                        'kind':match['kind'],'stage':match['stage'],'reference':reference})[:16]
                group_key=group_keys[stage_key]
                group=groups.setdefault(group_key,{'id':group_key,'kind':match['kind'],'stage':match['stage'],
                    'scenario':config.get('scenario',{}),'runs':set(),'models':{},'internal_matches':0})
                group['runs'].add(run['id'])
                for side,sid in candidates:
                    opponent=match['sides'][1-side]
                    if match['kind']=='competition' and (opponent in sessions or opponent in frozen) and participant_key(sid)==participant_key(opponent):
                        if side==0:group['internal_matches']+=1
                        continue
                    state=sessions.get(sid,{})
                    round_number,condition=track(sid)
                    key=digest({'descriptor':participant_key(sid),'round':round_number,'condition':condition})[:16]
                    row=group['models'].setdefault(key,{'id':key,'name':descriptor(sid)['variant'],
                        'round':round_number,'condition':condition,
                        'is_reference':sid in frozen or models.get(state.get('model'),{}).get('provider')=='mock',
                        'model_size_billion':model_size(sid),
                        'wins':0,'draws':0,'losses':0,'failed':0,'conversations':defaultdict(lambda:[0,0,None,None,None])})
                    if row['model_size_billion']!=model_size(sid):row['model_size_billion']=None
                    if not done:row['failed']+=1;continue
                    outcome='draws' if result.get('winner_side')==-1 else 'wins' if result.get('winner_side')==side else 'losses'
                    row[outcome]+=1
                    point=.5 if outcome=='draws' else 1 if outcome=='wins' else 0
                    entry=row['conversations'][(run['id'],sid)];entry[0]+=point;entry[1]+=1
                    if sid in sessions:
                        entry[2]=float(state.get('cost_spent') or '0') if not state.get('reconciliation_required') and not float(state.get('money_reserved') or '0') else None
                        entry[3]=state.get('wall_seconds')
                        entry[4]=state.get('steps',0)
        for group in groups.values():
            group['runs']=sorted(group['runs'])
            for row in group['models'].values():
                conversations=list(row.pop('conversations').values())
                averages=[points/count for points,count,*_ in conversations if count]
                row['score']=sum(averages)/len(averages) if averages else None
                row['conversations']=len(averages)
                row['score_per_billion']=row['score']/row['model_size_billion'] if row['score'] is not None and row['model_size_billion'] else None
                for field,index in (('mean_cost_usd',2),('mean_wall_seconds',3),('mean_tool_calls',4)):
                    values=[value[index] for value in conversations]
                    row[field]=sum(values)/len(values) if values and all(value is not None for value in values) else None
                row['total_tool_calls']=sum(value[4] for value in conversations) if all(value[4] is not None for value in conversations) else None
            group['models']=sorted(group['models'].values(),key=lambda row:-(row['score'] if row['score'] is not None else -1))
        for row in [totals,*resources.values()]:
            for key in ('known_cost_usd','reserved_usd'):row[key]=str(row[key])
        return {'totals':totals,'models':list(resources.values()),'groups':list(groups.values()),'excluded':excluded}
