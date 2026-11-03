import json
import unittest
from arena.core import scratch_directory, write_json
from arena.experiment import Journal
from arena_web.data import Store
from arena_web.server import Application


class ProviderDiagnosticsTests(unittest.TestCase):
    def test_unavailable_branch_exposes_origin_without_prompt_or_credentials(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=store.runs/'probe'
            write_json(root/'experiment.json',{'config':{'models':[{'id':'target','provider':'openai','model':'gpt-6.1-sol','parameters':{'reasoning_effort':'high'}}]}})
            journal=Journal(root)
            try:
                state={'model':'target','generation':0,'status':'provider_unavailable','calls':1,'history':[],
                       'failure':{'message':'Provider HTTP 400: Bad Request'}}
                journal.save('target-r0',state,'model_intent',{'request':{
                    'endpoint':'https://api.openai.com/v1/responses','headers':{'Authorization':'DO_NOT_EXPORT_KEY'},
                    'body':{'model':'gpt-6.1-sol','reasoning':{'effort':'high'},'input':[{'role':'user','content':'DO_NOT_EXPORT_PROMPT'}]}}})
                journal.save('target-r0',state,'provider_failure',{'error':'Bad Request','response':{'raw':'DO_NOT_EXPORT_RAW'}})
                journal.save('child',{**state,'calls':0,'parent':'target-r0','status':'no_submission'},'branch_unavailable',{'reason':'No G0 submission'})
            finally:journal.db.close()
            app=Application(store)
            try:
                data=app.get('/api/provider-diagnostics',{'run':['probe'],'session':['child']})
                self.assertEqual(data['origin_session'],'target-r0')
                self.assertEqual(data['failure_event'],{'error':'Bad Request'})
                self.assertEqual(data['endpoint'],'https://api.openai.com/v1/responses')
                self.assertEqual(data['request_shape']['reasoning'],{'effort':'high'})
                self.assertNotIn('DO_NOT_EXPORT',json.dumps(data))
                details=store.session_diagnostics('probe','child')
                self.assertEqual(details['failure_origin'],'target-r0')
            finally:app.jobs.close()
