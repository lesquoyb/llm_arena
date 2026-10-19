"""Streaming previews never execute partial calls or discard final usage."""
import json
from unittest import TestCase, mock
from arena.streaming import stream_json
from arena.api_providers import ProviderFailure, APIProvider


class Response:
    headers={'Content-Type':'text/event-stream','x-request-id':'fixture-request'}
    def __init__(self,events): self.events=events
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def __iter__(self):
        for event in self.events:
            yield ('data: '+json.dumps(event)+'\n\n').encode()
        yield b'data: [DONE]\n\n'


class Progress:
    def __init__(self): self.snapshots=[]
    def publish(self,value,force=False): self.snapshots.append(value)


class StreamingTests(TestCase):
    def test_chat_deltas_reconstruct_tools_reasoning_and_final_usage(self):
        events=[{'choices':[{'index':0,'delta':{'reasoning_content':'Think '}}]},
                {'choices':[{'index':0,'delta':{'reasoning_content':'first','tool_calls':[{'index':0,'id':'call-1','function':{'name':'write_file','arguments':'{"path":'}}]}}]},
                {'choices':[{'index':0,'delta':{'tool_calls':[{'index':0,'function':{'arguments':'"main.leek"}'}}]},'finish_reason':'tool_calls'}]},
                {'choices':[],'usage':{'prompt_tokens':100,'completion_tokens':20}}]
        progress=Progress()
        with mock.patch('arena.streaming.request.urlopen',return_value=Response(events)):
            result,rid=stream_json('https://example.com/v1/chat/completions',{'stream':True},{},30,progress)
        message=result['choices'][0]['message']
        self.assertEqual(message['reasoning_content'],'Think first')
        self.assertEqual(json.loads(message['tool_calls'][0]['function']['arguments']),{'path':'main.leek'})
        self.assertEqual(result['usage']['prompt_tokens'],100)
        self.assertEqual(result['stream_events'],events)
        self.assertEqual(rid,'fixture-request')
        self.assertTrue(any(snapshot['phase']=='streaming' for snapshot in progress.snapshots))
        self.assertEqual(progress.snapshots[-1]['phase'],'completed')

    def test_responses_completion_retains_native_output_and_usage(self):
        final={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Hello'}]}],
               'usage':{'input_tokens':12,'output_tokens':2}}
        events=[{'type':'response.output_text.delta','delta':'Hello'},
                {'type':'response.completed','response':final}]
        with mock.patch('arena.streaming.request.urlopen',return_value=Response(events)):
            result,_=stream_json('https://example.com/v1/responses',{'stream':True},{},30,Progress())
        self.assertEqual(result['usage'],final['usage'])
        self.assertEqual(result['output'],final['output'])
        json.dumps(result)  # The final receipt must not reference itself through stream events.

    def test_incomplete_stream_is_uncertain_and_keeps_a_partial_preview(self):
        progress=Progress()
        with mock.patch('arena.streaming.request.urlopen',return_value=Response([{'choices':[{'delta':{'content':'partial'}}]}])):
            with self.assertRaises(ProviderFailure) as context:
                stream_json('https://example.com/v1/chat/completions',{'stream':True},{},30,progress)
        self.assertTrue(context.exception.uncertain)
        self.assertEqual(progress.snapshots[-1]['phase'],'interrupted')
        self.assertEqual(progress.snapshots[-1]['text'],'partial')

    def test_only_streaming_chat_requests_ask_for_stream_usage(self):
        model={'provider':'openai-compatible','model':'local','_stream':True}
        result=APIProvider(model).payload([],[],None)
        self.assertTrue(result['stream'])
        self.assertTrue(result['stream_options']['include_usage'])
        self.assertNotIn('stream',APIProvider({**model,'_stream':False}).payload([],[],None))
