"""Copy selected frozen submissions into a provider-free tournament bundle."""
import argparse
import json
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arena.core import ArenaError, STATE_ROOT, copy_submission, digest, read_json, submission, write_json, load_manifest
from arena_web.data import Store


def freeze(selection, out, seeds, catalog=None):
    if catalog is None:
        path=STATE_ROOT/'ui/participants.json'
        catalog=read_json(path) if path.is_file() else []
    selection=Path(selection).resolve(); choices=read_json(selection)
    if not isinstance(choices,list) or len(choices)<2: raise ArenaError('Select at least two {run, session} objects')
    prepared=[];scenario=None
    with TemporaryDirectory(prefix='arena-freeze-reader-') as temporary:
        for index,choice in enumerate(choices,1):
            root=(selection.parent/choice['run']).resolve()
            metadata=read_json(root/'experiment.json');config=metadata['config']
            from arena.roster import effective
            config=effective(root,config)
            if scenario is not None and digest(scenario)!=digest(config['scenario']):
                raise ArenaError('Selected submissions have different scenarios; evaluate those in separate bundles')
            scenario=config['scenario']
            store=Store(root.parent,Path(temporary));state=store.session(root.name,choice['session'])
            info=state.get('submission')
            if not info: raise ArenaError('No frozen submission: '+choice['session'])
            source=root/'sessions'/choice['session']/'submission'
            if submission(source,info['entrypoint'])!=info: raise ArenaError('Submitted source changed')
            model=next(m for m in config['models'] if m['id']==state['model'])
            identifier=choice.get('id') or f"p{index:03}-"+choice['session'][:40]+'-'+info['sha256'][:8]
            origin={'run':root.name,'run_id':digest({'path':str(root),'identity':metadata})[:20],'session':choice['session'],'variant':state['model'],'provider':model['provider'],
                    'model':model.get('model',model.get('profile')),'parameters':{**model.get('parameters',{}),**state.get('provider_parameter_overrides',{})},
                    'round':state.get('generation',0)+1,'condition':state.get('condition','initial'),'replicate':state['replicate'],'model_size_billion':store.model_size(model,catalog=catalog)}
            prepared.append((identifier,source,info,origin))
    identifiers=[row[0] for row in prepared]
    if len(set(identifiers))!=len(identifiers) or any(not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}',value) for value in identifiers):
        raise ArenaError('Strategy IDs must be unique and contain 1–64 letters, digits, underscores or hyphens')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    strategies=[]
    for identifier,source,info,origin in prepared:
        # Local paths are generated, never derived from a participant-supplied identifier.
        target=out/'strategies'/f'{len(strategies)+1:03}'
        copy_submission(source,target,info)
        strategies.append({'id':identifier,'path':target.relative_to(out).as_posix(),'entrypoint':info['entrypoint'],'origin':origin})
    manifest=out/'manifest.json'
    write_json(manifest,{'name':'Frozen strategy benchmark','seeds':seeds,'include_mirrors':False,'scenario':scenario,'strategies':strategies})
    load_manifest(manifest)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection',type=Path,nargs='?',help='JSON array of {run,session,id?}; run paths are relative to this file')
    parser.add_argument('--initial-from',nargs='+',type=Path,help='Select all frozen initial-round submissions from these runs; record missing submissions')
    parser.add_argument('--out',type=Path,required=True,help='New bundle directory')
    parser.add_argument('--seeds',required=True,help='Comma-separated evaluation seeds; use held-out seeds for the final benchmark')
    args=parser.parse_args()
    if bool(args.selection)==bool(args.initial_from): parser.error('Choose a selection file or --initial-from runs')
    seeds=[int(v.strip()) for v in args.seeds.split(',')]
    if args.selection:
        print(freeze(args.selection,args.out,seeds))
    else:
        selected=[];missing=[]
        with TemporaryDirectory(prefix='arena-initial-selection-') as temporary:
            for root in args.initial_from:
                root=root.resolve();store=Store(root.parent,Path(temporary)/'ui')
                states=store.states(root,('model','generation','status','submission'))
                if not states: raise ArenaError('No generated sessions in '+str(root))
                for sid,state in states.items():
                    if state.get('generation',0)!=0: continue
                    if state.get('submission'): selected.append({'run':str(root),'session':sid})
                    else: missing.append({'run':str(root),'session':sid,'status':state.get('status')})
            selection=Path(temporary)/'selection.json';write_json(selection,selected)
            result=freeze(selection,args.out,seeds)
            write_json(args.out.resolve()/'omissions.json',missing)
            print(json.dumps({'manifest':str(result),'strategies':len(selected),'missing_submissions':len(missing)},indent=2))
