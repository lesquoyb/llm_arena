import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from arena.core import ROOT, scratch_directory, submission, write_json
from arena.compiler_diagnostics import CATALOG, compilation_rows
from arena.preparation import Preparation


class CompilerDiagnosticsTests(unittest.TestCase):
    def test_pinned_error_ids_match_the_observed_compiler_report(self):
        assessment = {'diagnostics': [
            [0,'main.leek',12,4,12,5,35],
            [0,'main.leek',16,4,16,5,36],
            [0,'main.leek',15,8,15,17,33,['moveResult']],
            [0,'main.leek',29,15,29,23,40],
            [1,'main.leek',22,23,22,25,93],
            [1,'main.leek',29,15,29,47,124,['(any, any)','(integer)']]]}
        rows = compilation_rows(assessment)
        self.assertEqual(rows[0]['message'],'Expected a value or expression')
        self.assertEqual(rows[1]['name'],'CANT_ADD_INSTRUCTION_AFTER_BREAK')
        self.assertEqual(rows[2]['message'],'Unknown variable or function: moveResult')
        self.assertEqual(rows[2]['line'],15)
        self.assertEqual(rows[3]['message'],'Incorrect number of function arguments')
        self.assertEqual(rows[4]['severity'],'warning')
        self.assertEqual(rows[4]['name'],'TRIPLE_EQUALS_DEPRECATED')
        self.assertIn('(integer)',rows[5]['message'])
        self.assertEqual(sum(row['severity']=='error' for row in rows),4)
        self.assertEqual(CATALOG['leekscript_commit'],json.loads((ROOT/'engine.lock.json').read_text())['leekscript_commit'])

    def test_member_entrypoints_unknown_codes_and_other_engine_versions(self):
        rows=compilation_rows({'diagnostics':[], 'member_analyses':{
            'support.leek':{'diagnostics':[[0,'helper.leek',3,1,3,4,9999,['example']]]}}})
        self.assertEqual(rows[0]['entrypoint'],'support.leek')
        self.assertEqual(rows[0]['message'],'Compiler diagnostic 9999: example')
        row=compilation_rows({'diagnostics':[[0,'main.leek',1,1,1,2,33,['x']]]},
                             {'lock':{'leekscript_commit':'different'}})[0]
        self.assertIsNone(row['name'])
        self.assertEqual(row['message'],'Compiler diagnostic 33: x')

    def test_native_and_mcp_analysis_dispatcher_returns_readable_errors_without_changing_cached_raw_result(self):
        with scratch_directory() as root:
            raw={'status':'invalid','diagnostics':[[0,'main.leek',1,4,1,8,33,['missingVariable']]]}
            def analyze(source,entry,out):
                write_json(out/'provenance.json',{'submission':submission(source,entry)})
                write_json(out/'result.json',raw)
                return raw
            engine=SimpleNamespace(identity={},analyze=mock.Mock(side_effect=analyze))
            tools=Preparation(root/'session',root/'docs',engine,{})
            tools.call('write_file',{'path':'main.leek','content':'return missingVariable'},'call-1-tool-0')
            first=tools.call('analyze',{},'call-2-tool-0')
            second=tools.call('analyze',{},'call-2-tool-0')
            self.assertEqual(first,second)
            self.assertEqual(engine.analyze.call_count,1)
            self.assertEqual(first['diagnostic_messages'][0]['message'],'Unknown variable or function: missingVariable')
            self.assertEqual(first['diagnostics'],raw['diagnostics'])
            self.assertEqual(json.loads((root/'session/tools/call-2-tool-0/result.json').read_text()),raw)
            self.assertIn('final saved sources',first['guide'])
