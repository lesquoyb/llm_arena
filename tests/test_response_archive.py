"""Transport archives stay lossless without quadratic checkpoint histories."""
import json
from unittest import TestCase
from arena.core import ArenaError, scratch_directory
from arena.experiment import Journal
from arena.api_providers import APIProvider
from arena_web.data import Store


class ResponseArchiveTests(TestCase):
    def test_checkpoint_is_small_and_full_transport_record_remains_accessible(self):
        with scratch_directory() as root:
            run=root/'runs'/'example';run.mkdir(parents=True)
            journal=Journal(run)
            model={'provider':'openai-compatible','model':'example'}
            first={'role':'user','content':'Keep the instructions'}
            response={'role':'assistant','native':{'role':'assistant','content':'Answer'},
                      'sent_parameters':{'messages':['large']*10000,'seed':7},'raw':{'complete':'response'}}
            state={'status':'running','history':[first,response],'pending':response}
            original=APIProvider(model).payload(state['history'],[],None)
            try:
                journal.save('model-r0',state,'model_response',response)
                journal.verify()
                saved=journal.state('model-r0')
                self.assertLess(len(json.dumps(saved)),2000)
                self.assertNotIn('sent_parameters',saved['history'][1])
                self.assertNotIn('raw',saved['pending'])
                self.assertEqual(APIProvider(model).payload(saved['history'],[],None),original)
            finally:
                journal.db.close()
            store=Store(root/'runs',root/'ui')
            full=store.message('example','model-r0',1)['message']
            self.assertEqual(full['sent_parameters'],response['sent_parameters'])
            self.assertEqual(full['raw'],response['raw'])
            reference=saved['history'][1]['response_artifact']
            (run/reference['artifact']).write_text('{}')
            with self.assertRaisesRegex(ArenaError,'Archived model response changed'):
                store.message('example','model-r0',1)
