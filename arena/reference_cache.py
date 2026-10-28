"""Content-addressed, verified replays for fights between fixed references."""
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from .core import ArenaError, STATE_ROOT, digest, file_hash, file_lock, is_link, make_scenario, read_json, submission, write_json


def _request(engine, infos, config, seed):
    return {'schema_version':1,'engine':engine.identity,'timeout_seconds':engine.timeout,
            'submissions':infos,
            'scenario':make_scenario(config,[info['entrypoint'] for info in infos],seed,[info.get('team') for info in infos])}


def _directory(engine):
    return Path(getattr(engine,'reference_cache_directory',STATE_ROOT/'reference-fights'))


def _read(entry, request):
    try:
        if is_link(entry):return None
        manifest=read_json(entry/'cache.json')
        if manifest.get('request')!=request or manifest.get('sha256')!=digest({k:v for k,v in manifest.items() if k!='sha256'}):return None
        files=manifest.get('files',{})
        if not {'result.json','outcome.json','scenario.json','provenance.json'}<=set(files):return None
        for name,expected in files.items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts or not (entry/'files'/relative).resolve().is_relative_to((entry/'files').resolve()):return None
            path=entry/'files'/relative
            if any(is_link(part) for part in [path,*path.parents]) or file_hash(path)!=expected:return None
        result=read_json(entry/'files/result.json');provenance=read_json(entry/'files/provenance.json')
        if (result.get('status')!='completed' or result.get('outcome_sha256')!=files['outcome.json'] or
                provenance.get('engine')!=request['engine'] or provenance.get('submissions')!=request['submissions'] or
                provenance.get('scenario_sha256')!=digest(request['scenario']) or read_json(entry/'files/scenario.json')!=request['scenario']):return None
        for side,info in enumerate(request['submissions'],1):
            if submission(entry/'files/strategies'/str(side),info['entrypoint'])!=info:return None
        return manifest
    except (OSError,ValueError,KeyError,TypeError,ArenaError):return None


def seed(engine, infos, config, seed_value, work):
    """Publish a verified existing fight too, without rewriting its run artifacts."""
    request=_request(engine,infos,config,seed_value);key=digest(request);root=_directory(engine);entry=root/key
    if (entry/'cache.json').is_file():return
    if any(is_link(path) for path in [work,*work.rglob('*')]):return
    root.mkdir(parents=True,exist_ok=True)
    try:
        with file_lock(root/'locks'/(key+'.lock')):
            if (entry/'cache.json').is_file():return
            with TemporaryDirectory(prefix='reference-',dir=root) as temporary:
                staged=Path(temporary)/'entry';shutil.copytree(work,staged/'files')
                files={path.relative_to(staged/'files').as_posix():file_hash(path) for path in sorted((staged/'files').rglob('*')) if path.is_file()}
                manifest={'request':request,'files':files};manifest['sha256']=digest(manifest)
                write_json(staged/'cache.json',manifest)
                if _read(staged,request) is None:return
                if entry.exists():entry.rename(root/('invalid-'+key+'-'+uuid4().hex))
                staged.rename(entry)
    except ArenaError as error:
        if str(error)!='Another process is writing these artifacts':raise
        # Concurrent first misses may both execute; publication never blocks a run.


def fight(engine, sources, infos, config, seed_value, work):
    """Use the full replay only when both fixed-reference inputs match exactly."""
    request=_request(engine,infos,config,seed_value);key=digest(request);entry=_directory(engine)/key
    for source,info in zip(sources,infos):
        if submission(Path(source),info['entrypoint'])!=info:raise ArenaError('Fixed reference source changed')
    manifest=_read(entry,request) if (entry/'cache.json').is_file() else None
    if manifest:
        started=time.monotonic();shutil.copytree(entry/'files',work)
        # Validate the materialized snapshot too; every competition stays portable.
        if any(file_hash(work/name)!=expected for name,expected in manifest['files'].items()):
            raise ArenaError('Reference cache changed while its replay was copied')
        result=read_json(work/'result.json')
        original_elapsed=(result.get('reference_cache') or {}).get('original_elapsed_seconds',result.get('elapsed_seconds'))
        receipt={'hit':True,'key':key,'original_elapsed_seconds':original_elapsed,'reuse_seconds':time.monotonic()-started}
        result.update(elapsed_seconds=0,reference_cache=receipt)
        provenance=read_json(work/'provenance.json');provenance['reference_cache']=receipt
        write_json(work/'provenance.json',provenance);write_json(work/'result.json',result)
        print('Reference replay cache hit: '+key[:12],flush=True)
        return result
    result=engine.fight(sources,infos,config,seed_value,work)
    if result.get('status')=='completed':
        # An invalid derived cache can be rebuilt; prior run artifacts are untouched.
        if (entry/'cache.json').is_file():
            root=_directory(engine)
            try:
                with file_lock(root/'locks'/(key+'.lock')):
                    if _read(entry,request) is None:entry.rename(root/('invalid-'+key+'-'+uuid4().hex))
            except ArenaError as error:
                if str(error)!='Another process is writing these artifacts':raise
        result={**result,'reference_cache':{'hit':False,'key':key,'original_elapsed_seconds':result.get('elapsed_seconds')}}
        write_json(work/'result.json',result)
        seed(engine,infos,config,seed_value,work)
    return result
