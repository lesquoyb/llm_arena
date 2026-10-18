import unittest
from arena.core import ArenaError, scratch_directory, write_json
from arena.preparation import Preparation
from arena.compiler_diagnostics import readable_analysis, compilation_rows


class APILookupTests(unittest.TestCase):
    def test_exact_search_is_small_and_legacy_name_explains_replacement(self):
        with scratch_directory() as tmp:
            write_json(tmp/'docs/leekscript-v1/api.json', {'functions':{
                'getEntity':{'signatures':['[] => integer']},
                'getEntityOnCell':{'signatures':['[integer] => integer']}}, 'constants':{'USE_SUCCESS':1}})
            tools=Preparation(tmp/'session',tmp/'docs',None,{})
            exact=tools.call('lookup_api',{'query':'getEntity()'},'1')
            self.assertEqual(exact['matches'],1)
            self.assertEqual(exact['results'][0]['name'],'getEntity')
            self.assertEqual(tools.call('lookup_api',{'query':'entity'},'2')['matches'],2)
            self.assertIn('getEntity()',tools.call('lookup_api',{'query':'getLeek'},'3')['hint'])
            with self.assertRaises(ArenaError):tools.call('lookup_api',{'query':''},'4')

    def test_removed_function_versions_and_source_are_explained(self):
        diagnostic={'diagnostics':[[0,'main.leek',1,11,1,17,94,['3','4']]]}
        with scratch_directory() as tmp:
            (tmp/'main.leek').write_text('var self = getLeek();\n',encoding='utf-8')
            row=readable_analysis(diagnostic,source_root=tmp)['diagnostic_messages'][0]
            self.assertIn('LeekScript 3',row['message'])
            self.assertIn('LeekScript 4',row['message'])
            self.assertIn('getEntity()',row['hint'])
            self.assertEqual(row['source_line'],'var self = getLeek();')
            self.assertEqual(compilation_rows(diagnostic)[0]['message'],row['message'])
