"""Engine input staging and timing, independent of an installed JVM."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from arena.engine import Engine
from arena.core import file_hash


class EngineStagingTests(unittest.TestCase):
    def test_temporary_engine_data_are_removed_and_copy_fallback_is_portable(self):
        original=subprocess.Popen
        for fallback in (False,True):
            with self.subTest(fallback=fallback),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);data=root/'pinned';data.mkdir();catalog=data/'catalog.json'
                catalog.write_text('{}',encoding='utf-8');expected=file_hash(catalog)
                work=root/'work';work.mkdir()
                engine=object.__new__(Engine)
                engine.metadata={'data':str(data),'java':sys.executable,'classes':str(root/'classes'),'jar':str(root/'fixture.jar')}
                engine.worker_options=[];engine.backend='process';engine.timeout=10
                observed=[]
                def spawn(args,**kwargs):
                    observed.append((work/'data/catalog.json').samefile(catalog))
                    output={'success':True,'winner':-1,'duration':1,'fight':{},'team_metrics':{}}
                    program='from pathlib import Path;Path("outcome.json").write_text('+repr(json.dumps(output))+',encoding="utf-8")'
                    return original([sys.executable,'-c',program],**kwargs)
                with mock.patch('arena.engine.subprocess.Popen',side_effect=spawn):
                    if fallback:
                        with mock.patch('arena.engine.os.link',side_effect=OSError('Cross-volume fixture')):
                            result=engine.invoke(work,'fight','scenario.json')
                    else:result=engine.invoke(work,'fight','scenario.json')
                self.assertEqual(result['status'],'completed')
                self.assertFalse((work/'data').exists())
                self.assertEqual(file_hash(catalog),expected)
                self.assertGreater(result['timings']['java_process_seconds'],0)
                if fallback:
                    self.assertEqual(observed,[False])
                    self.assertEqual(result['timings']['data_copied_files'],1)
