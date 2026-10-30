from unittest import TestCase
from arena.calibration_transcript import export


class TranscriptExportTests(TestCase):
    def test_export_contains_every_turn_without_duplicating_transport_histories(self):
        history=[{'role':'system','content':'Initial prompt'}]
        history += [{'role':'assistant','native':{'reasoning_content':f'Plan {i}'},
                     'raw':{'duplicated':'transport'},'sent_parameters':{'messages':['duplicate']},
                     'response_artifact':{'artifact':'receipt.json'}} for i in range(35)]
        history += [{'role':'tool','name':'read_file','result':{'content':'full file'}}]
        result=export({'history':history,'message_times':[1]*len(history),'status':'submitted'})
        self.assertEqual(len(result['messages']),37)
        self.assertEqual(result['messages'][0]['content'],'Initial prompt')
        self.assertEqual(result['messages'][-1]['result']['content'],'full file')
        self.assertEqual(result['statistics']['reasoning_messages'],35)
        self.assertEqual(result['messages'][1]['recorded_at'],1)
        self.assertNotIn('sent_parameters',result['messages'][1])
        self.assertNotIn('raw',result['messages'][1])
        self.assertEqual(result['readable_reasoning'][-1]['message_index'],35)

    def test_encrypted_reasoning_stays_in_transcript_but_is_not_marked_readable(self):
        message={'role':'assistant','native':{'responses_output':[{'type':'reasoning','encrypted_content':'opaque'}]}}
        result=export({'history':[message]})
        self.assertEqual(result['statistics']['reasoning_messages'],0)
        self.assertEqual(result['statistics']['serialized_reasoning_characters'],0)
        self.assertEqual(result['readable_reasoning'],[])
        self.assertEqual(result['messages'][0]['native'],message['native'])
