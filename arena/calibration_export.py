"""Recover a candidate's cumulative learning material without changing the checkout."""
import copy
import difflib
import hashlib
import io
import json
import zipfile
from .core import ROOT,read_json
from .calibration_documents import originals


def bundle(study,review):
    number=review['candidate']-1
    config=copy.deepcopy(review['config'])
    source=study/'trials'/f'{review["source_candidate"]-1:03}'/'corpus'
    baseline=study/'trials/000/corpus'
    selected=study/'trials'/f'{number:03}'/'corpus'
    before={};after={}
    for name,text in originals().items():
        before[name]=(baseline/name).read_text(encoding='utf-8') if (baseline/name).exists() else text
        inherited=(source/name).read_text(encoding='utf-8') if (source/name).exists() else before[name]
        after[name]=(selected/name).read_text(encoding='utf-8') if (selected/name).exists() else config.get('reference_documents',{}).get(name,inherited)
    changed={name:text for name,text in after.items() if text!=before[name]}
    patch=[];bases={}
    for name,text in changed.items():
        current=(ROOT/'docs'/name).read_text(encoding='utf-8')
        bases['docs/'+name]=hashlib.sha256(current.encode('utf-8')).hexdigest()
        for line in difflib.unified_diff(current.splitlines(True),text.splitlines(True),fromfile='a/docs/'+name,tofile='b/docs/'+name):
            patch.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    # Pin all editable reference text so the exported configuration can be reused
    # independently of later changes to the repository's default documents.
    config['reference_documents']=after
    state=read_json(study/'study.json')
    manifest={'study':study.name,'candidate':review['candidate'],'source_candidate':review['source_candidate'],
              'decision':review['decision'],'current_best':review['current_best'],
              'evaluated':number<len(state.get('trials',[])),
              'changed_documents_since_initial_candidate':sorted('docs/'+name for name in changed),
              'patch_base_sha256':bases,
              'note':'Documents include cumulative analyst edits since the initial candidate. Patch is based on the current local repository contents at export time. Export does not apply changes.'}
    files={'system-prompt.txt':config['prompt'], 'tools.json':json.dumps(config['tools'],indent=2)+'\n',
           'calibration.json':json.dumps(config,ensure_ascii=False,indent=2)+'\n',
           'manifest.json':json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',
           'documents.patch':''.join(patch),
           'README.txt':'''Recovered calibration learning material

system-prompt.txt contains the selected system prompt.
tools.json contains its enabled Arena tools.
calibration.json contains the full reusable candidate configuration and frozen
editable reference documents. This export does not change application defaults.

Only documents changed since the study's initial candidate are in docs/.
Their paths match the repository. Copy them deliberately or, from the repository
root, check and apply the patch (replace the path to the extracted folder):

  git apply --check path/to/export/documents.patch
  git apply path/to/export/documents.patch

An empty patch means no document changes need applying to this checkout.
The patch was generated against local repository contents at export time.
If files changed afterwards, check the differences before applying it.
The system prompt is a separate text file; it does not patch Python source.

To evaluate this configuration using the activated environment:
  python -m arena calibrate run path/to/export/calibration.json --out calibrations/recovered-study
Add --automatic to continue automatic optimization with its configured analyst.
Provider credentials must still come from the local environment or application.

Inspect manifest.json: an exported proposal can be untested or rejected.
This ZIP does not mean it is the current best candidate. No model calls are made.
'''}
    files.update({'docs/'+name:text for name,text in changed.items()})
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,text in files.items(): archive.writestr(name,text.encode('utf-8'))
    return buffer.getvalue()
