"""The language importer keeps syntax and omits complete battle-strategy listings."""
from pathlib import Path
from unittest import TestCase
from scripts.import_language_docs import clean, import_pages, PAGES
from arena.core import scratch_directory, read_json
from arena.tool_schemas import TOOLS
from arena.experiment import PROMPT


class LanguageDocumentationTests(TestCase):
    def test_clean_keeps_code_and_removes_widgets_and_full_strategy_tail(self):
        content='# Lists\r\n{{ tutorial-progress }}\r\n[[Variables]]\r\n```leekscript\nvar a = [[1], [2]];\nvar b = <1, 2>;\n```\n## ❓ Quiz\nFULL_STRATEGY_SENTINEL'
        result=clean(content,'❓ Quiz')
        self.assertNotIn('{{',result)
        self.assertNotIn('FULL_STRATEGY_SENTINEL',result)
        self.assertIn('corpus/language/variables.md',result)
        self.assertIn('var a = [[1], [2]];',result)
        self.assertIn('var b = <1, 2>;',result)

    def test_missing_chapter_boundary_leaves_published_docs_untouched(self):
        pages=[{'title':title,'language':'en','id':i,'content':'# '+title+'\n'+('## '+cutoff+'\n' if cutoff else '')}
               for i,(title,cutoff) in enumerate(PAGES.values(),1)]
        with scratch_directory() as out:
            destination=out/'language';manifest=out/'sources.json'
            count=import_pages(pages,destination,manifest)
            self.assertEqual(count,14)
            existing=(destination/'variables.md').read_bytes()
            self.assertEqual(len(read_json(manifest)['pages']),14)
            pages[1]['content']='# Variables\nMissing the expected heading'
            with self.assertRaises(ValueError): import_pages(pages,destination,manifest)
            self.assertEqual((destination/'variables.md').read_bytes(),existing)
            self.assertNotIn('source_url',(destination/'variables.md').read_text())

    def test_language_and_private_sparring_are_discoverable_without_extra_provider_tools(self):
        self.assertIn('corpus/language/cheatsheet.md',PROMPT)
        self.assertIn('opponent_entrypoint="sparring.leek"',PROMPT)
        tools={tool['name']:tool for tool in TOOLS}
        self.assertIn('corpus/language/index.md',tools['read_docs']['description'])
        self.assertIn('opponent_entrypoint',tools['test']['input_schema']['properties'])
