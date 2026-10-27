"""Flat, read-only multi-run tables. A fight and a model appearance are distinct."""
import csv
import json
from decimal import Decimal
from tempfile import TemporaryDirectory
from collections import defaultdict
from pathlib import Path
from .core import ArenaError, STATE_ROOT, digest, read_json, write_json
from arena_web.data import Store

METRICS = ('operations','errors','operation_limit_hits','damage_dealt','damage_taken','healing_given','healing_received','actions','cells_moved')


def _csv(path, rows, empty_fields):
    fields=list(dict.fromkeys(key for row in rows for key in row)) or empty_fields
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)


def export(runs, out, catalog=None):
    if catalog is None:
        path=STATE_ROOT/'ui/participants.json'
        catalog=read_json(path) if path.is_file() else []
    runs=[Path(root).resolve() for root in runs]
    if len(set(runs)) != len(runs): raise ArenaError('The same run was selected more than once')
    temporary=TemporaryDirectory(prefix="arena-benchmark-reader-")
    sessions, appearances, scores, run_index = [], [], [], []
    for root in runs:
        root=Path(root).resolve()
        store=Store(root.parent,Path(temporary.name))
        metadata=store.json(root/'experiment.json')
        if not metadata: raise ArenaError('Missing experiment.json: '+str(root))
        config=metadata.get('config') or metadata.get('manifest') or {}
        models={m['id']:m for m in config.get('models',[])}
        states=store.states(root)
        receipts=store.usage_receipts(root) if (root/'journal.sqlite').exists() else {}
        frozen={s['id']:s for s in config.get('strategies',[])}
        run_id=digest({'path':str(root),'identity':metadata})[:20]
        run_index.append({'run_id':run_id,'run':root.name,'directory':str(root),'name':config.get('name'),
                          'scenario_sha256':digest(config.get('scenario',{})),'engine_sha256':digest(metadata.get('engine',{}))})
        descriptors={}
        for sid,state in states.items():
            model=models.get(state['model'],{})
            receipt=receipts.get(sid,{})
            has_receipts=bool(receipt.get('responses'))
            measured=has_receipts and not receipt.get('missing_usage')
            descriptor={'run':root.name,'run_id':run_id,'participant':sid,'source_run_id':run_id,'source_run':root.name,'source_session':sid,'variant':state['model'],'provider':model.get('provider'),
                'model':model.get('model',model.get('profile')),'requested_parameters_json':json.dumps({**model.get('parameters',{}),**state.get('provider_parameter_overrides',{})},sort_keys=True),
                'replicate':state.get('replicate'),'round':state.get('generation',0)+1,'condition':state.get('condition','initial'),
                'scenario_sha256':digest(config.get('scenario',{})),'engine_sha256':digest(metadata.get('engine',{})),
                'strategy_sha256':state.get('submission',{}).get('sha256'),'model_size_billion':store.model_size(model,catalog=catalog)}
            descriptors[sid]=descriptor
            tokens={key:receipt.get(key) if measured else None if has_receipts else state.get(key) if state.get('token_usage_known') else None for key in ('input_tokens','output_tokens')}
            sessions.append({**descriptor,'status':state.get('status'),'validation':state.get('validity'),
                'has_submission':bool(state.get('submission')),'submission_mode':'automatic_budget' if state.get('submission') and state.get('status')=='budget_exhausted' else 'explicit' if state.get('submission') else 'none',
                'preparation_limits_json':json.dumps(config.get('budget_per_session',{}),sort_keys=True),
                'parallel_requests':config.get('parallel_requests',1),'shared_spending_limit_usd':config.get('spending',{}).get('max_total_usd'),'calls':state.get('calls',0),'tool_calls':state.get('steps',0),
                'preparation_matches':state.get('test_matches',0),'wall_seconds':state.get('wall_seconds'),
                'messages':len(state.get('history', [])),
                **{role+'_messages':sum(m.get('role')==role for m in state.get('history', [])) for role in ('system','user','assistant','tool')}, **tokens,
                'cache_creation_input_tokens':receipt.get('cache_creation_input_tokens') if measured and not receipt.get('missing_cache_creation_usage') else None,
                'cached_input_tokens':receipt.get('cached_input_tokens') if measured and not receipt.get('missing_cache_usage') else None,
                'reasoning_tokens':receipt.get('reasoning_tokens') if measured and not receipt.get('missing_reasoning_usage') else None,
                'usage_complete':bool(measured if has_receipts else state.get('token_usage_known')) and not state.get('in_flight') and state.get('status')!='needs_reconciliation',
                'cost_usd':None if state.get('status')=='needs_reconciliation' else str(Decimal(state.get('cost_spent','0')) + Decimal(receipt.get('cost_adjustment_usd','0'))),
                'recorded_cost_usd':state.get('cost_spent','0'),
                'reserved_usd':state.get('money_reserved','0')})
        for sid,strategy in frozen.items():
            origin=strategy.get('origin',{})
            descriptors[sid]={'run':root.name,'run_id':run_id,'participant':sid,'source_run_id':origin.get('run_id'),'source_run':origin.get('run'),'source_session':origin.get('session'),'variant':origin.get('variant',strategy.get('model',sid)),
                'provider':origin.get('provider'),'model':origin.get('model',strategy.get('model')),
                'requested_parameters_json':json.dumps(origin.get('parameters',{}),sort_keys=True),'replicate':origin.get('replicate',strategy.get('replicate')),
                'round':origin.get('round'),'condition':origin.get('condition','frozen'),
                'scenario_sha256':digest(config.get('scenario',{})),'engine_sha256':digest(metadata.get('engine',{})),
                'strategy_sha256':strategy.get('submission',{}).get('sha256'),'model_size_billion':origin.get('model_size_billion')}
        groups=defaultdict(list)
        for fight in store.matches(root.name)['matches']:
            for side,sid in enumerate(fight['sides']):
                descriptor=descriptors.get(sid,{'run':root.name,'run_id':run_id,'participant':sid,'variant':sid})
                result=fight['result'];done=result.get('status')=='completed'
                outcome=('draw' if result.get('winner_side')==-1 else 'win' if result.get('winner_side')==side else 'loss') if done else 'unscored'
                metrics=result.get('team_metrics',{}).get(str(side),{})
                row={**descriptor,'fight_id':digest({'run':run_id,'path':fight['path']}),'artifact_path':fight['path'],
                     'side':side,'opponent':fight['sides'][1-side],'kind':fight['kind'],'stage':fight['stage'],'seed':fight['seed'],
                     'mirror':fight['mirror'],'candidate':fight.get('candidate'),'is_candidate':fight.get('candidate')==sid,
                     'counts_toward_standings':fight['counts_toward_standings'],'status':result.get('status'),'outcome':outcome,
                     'points':None if not done else .5 if outcome=='draw' else int(outcome=='win'),
                     'turns':result.get('turns'),'elapsed_seconds':result.get('elapsed_seconds'),
                     **{key:metrics.get(key) for key in METRICS}}
                appearances.append(row)
                # Reference opponents appear in fights.csv, but are not candidate evaluations.
                if fight['mirror'] or (fight['kind']=='evaluation' and fight.get('candidate')!=sid): continue
                groups[(sid,fight['kind'],fight['stage'])].append(row)
        for (sid,kind,stage),rows in groups.items():
            done=[r for r in rows if r['outcome']!='unscored']
            scores.append({**descriptors.get(sid,{'run':root.name,'run_id':run_id,'participant':sid,'variant':sid}), 'kind':kind,'stage':stage,
                'completed':len(done),'failed':len(rows)-len(done),'wins':sum(r['outcome']=='win' for r in done),
                'draws':sum(r['outcome']=='draw' for r in done),'losses':sum(r['outcome']=='loss' for r in done),
                'score':sum(r['points'] for r in done)/len(done) if done else None})
    resource_fields = ('cost_usd','recorded_cost_usd','input_tokens','output_tokens','cached_input_tokens',
                       'cache_creation_input_tokens','reasoning_tokens','calls','tool_calls','messages',
                       'system_messages','user_messages','assistant_messages','tool_messages','wall_seconds','usage_complete')
    resources = {(row['run_id'],row['participant']):row for row in sessions}
    results = []
    for score in scores:
        resource = resources.get((score.get('source_run_id'),score.get('source_session')), {})
        results.append({**score, 'score_per_billion':score['score']/score['model_size_billion'] if score.get('score') is not None and score.get('model_size_billion') else None, **{key:resource.get(key) for key in resource_fields}})
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    write_json(out/'runs.json',run_index)
    _csv(out/'sessions.csv',sessions,['run','participant'])
    _csv(out/'fights.csv',appearances,['run','fight_id','side'])
    _csv(out/'scores.csv',scores,['run','participant','kind','stage'])
    _csv(out/'results.csv',results,['run','participant','kind','stage','score','cost_usd'])
    (out/'README.txt').write_text('UTF-8 CSV with BOM. Blank means unknown, not zero. runs.json maps run_id to original directories.\n'
        'results: participant/stage results joined to generation cost, tokens, messages and preparation wall seconds. Resource columns repeat across stages: never sum them across stages. Frozen origins require the source run in the export.\n'
        'sessions: one generated conversation. Costs and tokens belong here; join frozen origins via source_run_id/source_session, and do not sum costs after joining onto fights.\n'
        'fights: two rows per actual fight, one per side. Count distinct fight_id for unique fights.\n'
        'scores: one participant and stage; mirrors excluded. Training is separate; reference results count only the candidate.\n'
        'Do not average across scenarios, parameters, rounds, conditions or opponent panels unintentionally.\n'
        'Independent sampling units are generated strategies/replicates; fight seeds and both sides are paired observations.\n'
        'Static tournament rows carry origin metadata when exported with freeze_benchmark.py; they incur no new LLM calls.\n',encoding='utf-8')
    temporary.cleanup()
    return {'sessions':len(sessions),'fight_appearances':len(appearances),'score_rows':len(scores),'out':str(out)}
