import io
import json
import zipfile
from unittest import TestCase
from arena.calibration import defaults
from arena.calibration_export import bundle
from arena.core import scratch_directory,write_json


class LearningMaterialExportTests(TestCase):
    def test_export_recovers_cumulative_docs_even_when_last_edit_did_not_change_them(self):
        with scratch_directory() as root:
            base=defaults();selected={**base,'prompt':'Selected prompt','reference_documents':{'authoring.md':'# Cumulative edit\n'}}
            write_json(root/'study.json',{'trials':[{}, {}, {}]})
            for index,text in [(0,'# Original\n'),(1,'# Cumulative edit\n'),(2,'# Cumulative edit\n')]:
                path=root/f'trials/{index:03}/corpus/authoring.md';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
            review={'candidate':3,'source_candidate':2,'config':selected,'decision':'Rejected','current_best':False}
            with zipfile.ZipFile(io.BytesIO(bundle(root,review))) as archive:
                self.assertEqual(archive.read('system-prompt.txt').decode(),'Selected prompt')
                self.assertEqual(archive.read('docs/authoring.md').decode(),'# Cumulative edit\n')
                manifest=json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['changed_documents_since_initial_candidate'],['docs/authoring.md'])
                self.assertFalse(manifest['current_best'])
                self.assertIn('a/docs/authoring.md',archive.read('documents.patch').decode())
                self.assertEqual(json.loads(archive.read('calibration.json'))['reference_documents']['authoring.md'],'# Cumulative edit\n')
