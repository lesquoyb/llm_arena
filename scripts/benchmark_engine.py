#!/usr/bin/env python3
"""Compare native JVM presets on identical fights, without any model/API calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import threading
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.core import ArenaError, STATE_ROOT, read_json, submission, write_json
from arena.engine import Engine
from arena.jvm_options import PROFILES, settings
from arena.presets import simple_scenario
from arena.worker_resources import process_cpu_seconds


def resident_bytes(pid):
    """RSS/working set, including JVM native memory; unknown on unsupported hosts."""
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('size',wintypes.DWORD),('faults',wintypes.DWORD),
                    *[(name,ctypes.c_size_t) for name in ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]]
            kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=wintypes.HANDLE
            handle=kernel.OpenProcess(0x0410,False,pid)
            if not handle:return None
            try:
                value=Counters();value.size=ctypes.sizeof(value)
                query=ctypes.windll.psapi.GetProcessMemoryInfo
                query.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
                if query(handle,ctypes.byref(value),value.size):return value.working
            finally:kernel.CloseHandle(wintypes.HANDLE(handle))
        else:
            with open('/proc/'+str(pid)+'/status') as stream:
                for line in stream:
                    if line.startswith('VmRSS:'):return int(line.split()[1])*1024
    except (OSError,ValueError,AttributeError):pass
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',nargs='+',choices=PROFILES,default=['startup','throughput','optimizing','full'])
    parser.add_argument('--matches',type=int,default=64,help='Fights per profile, including cold start')
    parser.add_argument('--workers',type=int,default=min(4,os.cpu_count() or 1))
    parser.add_argument('--workload',choices=['mixed','short','long','compute'],default='mixed')
    parser.add_argument('--recycle',type=int,default=32)
    parser.add_argument('--fight-artifact',type=Path,help='Repeat an archived competition fight with its frozen sources and seed, without provider calls')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if min(args.matches,args.workers,args.recycle)<1:parser.error('matches, workers and recycle must be positive')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    root=(args.out or STATE_ROOT/'benchmarks'/('jvm-'+stamp+'-'+str(os.getpid()))).resolve()
    if root.exists():parser.error('Choose a new output directory to preserve previous benchmark records')
    root.mkdir(parents=True)
    source=root/'sources/compute';source.mkdir(parents=True)
    (source/'main.leek').write_text('var sum = 0; for (var i = 0; i < 50000; i++) { sum += i % 97; }\n'+(ROOT/'examples/strategies/human-weapon/main.leek').read_text(encoding='utf-8'),encoding='utf-8')
    def pair(a,b):return [Path(a),Path(b)]
    strategies=ROOT/'examples/strategies'
    cases={'short':(read_json(ROOT/'configs/offline-complete.json')['scenario'],pair(strategies/'rush',strategies/'single-shot')),
           'long':(simple_scenario(),pair(strategies/'turret',strategies/'passive')),
           'compute':(simple_scenario(),pair(source,strategies/'human-weapon'))}
    for name,(scenario,paths) in list(cases.items()):cases[name]=(scenario,paths,[submission(path) for path in paths])
    names=list(cases) if args.workload=='mixed' else [args.workload]
    archived_seed=None
    if args.fight_artifact:
        artifact=args.fight_artifact.resolve()
        provenance=read_json(artifact/'provenance.json')
        owner=next((parent for parent in artifact.parents if (parent/'experiment.json').exists() and 'config' in read_json(parent/'experiment.json')),None)
        if owner is None:raise ArenaError('Cannot find source competition configuration')
        scenario=read_json(owner/'experiment.json')['config']['scenario']
        paths=[artifact/'strategies'/str(side) for side in (1,2)]
        infos=provenance['submissions']
        if [submission(path,info['entrypoint']) for path,info in zip(paths,infos)]!=infos:raise ArenaError('Frozen sources changed')
        from arena.core import make_scenario
        saved=read_json(artifact/'scenario.json');archived_seed=saved['random_seed']
        if make_scenario(scenario,[info['entrypoint'] for info in infos],archived_seed,[info.get('team') for info in infos])!=saved:raise ArenaError('Saved scenario differs from competition configuration')
        cases={'archived':(scenario,paths,infos)};names=['archived']
    report={'matches_per_profile':args.matches,'workers':args.workers,'recycle_matches':args.recycle,'workload':args.workload,
            'cpu_count':os.cpu_count(),'profiles':[],'notes':'Engine only. Direct execution bypasses the reference replay cache. Cold starts are included. Peak RSS is sampled after completed fights.'}
    baseline={};guard=threading.Lock()
    for profile in args.profiles:
        engine=Engine()
        try:
            if not engine._jvm_pool:raise ArenaError('Rebuild native ArenaWorker with python -m arena setup before benchmarking')
            _,engine.worker_options,recycle=settings(True,{'ARENA_JVM_PROFILE':profile,'ARENA_JVM_RECYCLE_MATCHES':str(args.recycle)})
            engine._jvm_pool.recycle=recycle
            engine.identity.update(worker_jvm_profile=profile,worker_jvm_options=engine.worker_options,worker_jvm_recycle_matches=recycle)
            peak=[None];started=time.perf_counter();python_started=time.process_time()
            def fight(index):
                name=names[index%len(names)];scenario,paths,infos=cases[name];seed=archived_seed or 101+(index//len(names))%3
                result=engine.fight(paths,infos,scenario,seed,root/'fights'/profile/str(index))
                if result['status']!='completed':raise ArenaError(f'{profile} {name}: {result.get("error",result["status"])}')
                deterministic={'replay':result['replay_sha256'],'metrics':{side:{k:v for k,v in row.items() if k!='turn_elapsed_ns'} for side,row in result['team_metrics'].items()}}
                with guard:
                    key=(name,seed)
                    if key in baseline and baseline[key]!=deterministic:raise ArenaError(f'Game result changed for {profile}, {name}, seed {seed}')
                    baseline[key]=deterministic
                with engine._jvm_pool.lock:workers=list(engine._jvm_pool.all)
                memory=[resident_bytes(worker.process.pid) for worker in workers]
                if memory and all(value is not None for value in memory):
                    with guard:peak[0]=max(peak[0] or 0,sum(memory))
                return result
            with ThreadPoolExecutor(max_workers=args.workers) as workers:results=list(workers.map(fight,range(args.matches)))
            wall=time.perf_counter()-started
            row={'profile':profile,'flags':engine.worker_options,'matches':len(results),'wall_seconds':wall,
                 'matches_per_minute':60*len(results)/wall,'mean_fight_seconds':statistics.mean(r['elapsed_seconds'] for r in results),
                 'python_cpu_seconds':time.process_time()-python_started,
                 'java_cpu_seconds':sum(r['timings'].get('java_cpu_seconds',0) for r in results) if all('java_cpu_seconds' in r['timings'] for r in results) else None,
                 'sampled_peak_rss_bytes':peak[0],'jvm_starts':sum(not r['timings']['jvm_reused'] for r in results),
                 'replays_match':True,'java_version':engine.metadata['java_version']}
            report['profiles'].append(row);write_json(root/'report.json',report)
            print(json.dumps(row),flush=True)
        finally:engine.close()
    print('Report: '+str(root/'report.json'))


if __name__=='__main__':main()
