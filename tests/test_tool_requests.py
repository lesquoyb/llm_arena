"""Analyst development requests remain reports, not tool registrations."""
import unittest
from arena.core import ArenaError, scratch_directory, read_json
from arena.tool_requests import validate, write_report
from arena.tool_schemas import TOOLS


class ToolRequestTests(unittest.TestCase):
    def test_report_does_not_register_or_execute_requested_tools(self):
        names=[tool['name'] for tool in TOOLS]
        requests=[{'kind':'new_tool','tool':'inspect_example','problem':'No suitable inspector',
                   'proposed_change':'Add a read-only inspector','evidence':['target-r0-g1, message 4'],
                   'expected_benefit':'Fewer blind edits'}]
        with scratch_directory() as out:
            write_report(out,requests)
            self.assertEqual(read_json(out/'tool-requests.json'),requests)
            self.assertIn('target-r0-g1, message 4',(out/'tool-requests.md').read_text())
        self.assertEqual([tool['name'] for tool in TOOLS],names)
        self.assertNotIn('inspect_example',names)

    def test_malformed_recommendations_are_rejected(self):
        for requests in ({},[{}],[{'kind':'execute','problem':'x','proposed_change':'y'}]):
            with self.assertRaises(ArenaError): validate(requests)
