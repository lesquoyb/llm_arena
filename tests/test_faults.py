import unittest
from contextlib import closing
from arena.core import ROOT, read_json, write_json, scratch_directory
from arena.experiment import Journal, initial_state
from arena_web.data import Store
from arena_web.faults import report


class FaultTests(unittest.TestCase):
    def test_historical_receipts_separate_compilation_tools_and_provider_failures(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            config=read_json(ROOT/'configs/offline-complete.json')
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                model=config['models'][0];sid=model['id']+'-r0';state=initial_state(sid,model,config)
                journal.save(sid,state,'session_created')
                for name,value in [('invented',{'error':'Unknown tool'}),('read_docs',{'error':'Invalid offset: negative'}),('read_file',{'error':'File not found'}),('analyze',{'status':'invalid','diagnostic_messages':[{'severity':'error','message':'Unknown name'},{'severity':'warning','message':'Warning'}]}),('analyze',{'status':'valid'}),('validate_team',{'valid':False,'errors':['Too many weapons']})]:
                    journal.save(sid,state,'tool_reserved',{'name':name,'arguments':{}})
                    journal.save(sid,state,'tool_result',value)
                journal.save(sid,state,'provider_failure',{'error':'HTTP 429'})
            result=report(store,'run');row=result['sessions'][0]
            self.assertEqual((row['tool_calls'],row['tool_errors'],row['unknown_tools'],row['invalid_arguments'],row['other_tool_errors']),(6,3,1,1,1))
            self.assertEqual((row['analyses'],row['failed_analyses'],row['compiler_errors'],row['invalid_teams'],row['provider_failures']),(2,1,1,1,1))
            self.assertEqual(row['tool_error_rate'],.5)
            self.assertEqual(row['compile_failure_rate'],.5)
            self.assertEqual(result['incidents_total'],6)
            self.assertEqual(report(store,'run'),result)

    def test_engine_timeout_is_not_a_successful_compilation(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            config=read_json(ROOT/'configs/offline-complete.json')
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                model=config['models'][0];sid=model['id']+'-r0';state=initial_state(sid,model,config)
                journal.save(sid,state,'session_created')
                for value in ({'status':'valid'},{'status':'invalid'},{'status':'timeout'}):
                    journal.save(sid,state,'tool_reserved',{'name':'analyze','arguments':{}})
                    journal.save(sid,state,'tool_result',value)
            row=report(store,'run')['sessions'][0]
            self.assertEqual(row['analyses'],3)
            self.assertEqual(row['completed_analyses'],2)
            self.assertEqual(row['analysis_infrastructure_failures'],1)
            self.assertEqual(row['compile_failure_rate'],.5)
