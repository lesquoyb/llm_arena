"""Neither coordinator waits for the other's tools, replies or publication."""
import threading
import unittest
from unittest import mock
from arena.core import scratch_directory
from arena.experiment import Journal,initial_state
from arena.parallel import prepare
from arena.fight_coordinator import FightCoordinator
from test_parallel_requests import config,CoordinatorEngine


def response(provider,history,tools,limit):
    seen={message.get('name') for message in history if message['role']=='tool'}
    tool='write_file' if 'write_file' not in seen else 'analyze' if 'analyze' not in seen else 'submit'
    args={'path':'main.leek','content':'var v = 1;'} if tool=='write_file' else {}
    return {'role':'assistant','native':{'role':'assistant','content':''},'tool_calls':[
        {'id':tool,'name':tool,'arguments':args}],'usage':{'input_tokens':10,'output_tokens':1},'cost_usd':'0'}


class IndependentCoordinatorTests(unittest.TestCase):
    def test_conversation_finishes_while_engine_publication_is_blocked(self):
        value=config();value['models']=value['models'][:1];value['include_mirrors']=False
        model=value['models'][0];entered=threading.Event();release=threading.Event()
        with scratch_directory() as root:
            journal=Journal(root)
            def engine_progress(engine_journal):
                self.assertIsNot(engine_journal.db,journal.db)
                entered.set()
                if not release.wait(3):raise RuntimeError('Conversation stalled behind engine work')
                engine_journal.record('one-r0','independent_engine_fixture',{'saved':True})
            def respond(*args):
                if not entered.wait(3):raise RuntimeError('Independent engine coordinator did not start')
                result=response(*args)
                if result['tool_calls'][0]['name']=='submit':release.set()
                return result
            try:
                with mock.patch('arena.api_providers.APIProvider.respond',new=respond):
                    prepare([('one-r0',model)],value,root,journal,CoordinatorEngine(),on_progress=engine_progress,independent_fights=True)
                self.assertEqual(journal.state('one-r0')['status'],'submitted')
                journal.verify()
            finally:release.set();journal.db.close()

    def test_engine_saves_while_conversation_tool_is_blocked(self):
        value=config();value['models']=value['models'][:1];value['include_mirrors']=False
        model=value['models'][0];entered=threading.Event();saved=threading.Event()
        class BlockingTool(CoordinatorEngine):
            def analyze(self,*args):
                entered.set()
                if not saved.wait(3):raise RuntimeError('Engine work stalled behind conversation tool')
                return super().analyze(*args)
        with scratch_directory() as root:
            journal=Journal(root)
            def engine_progress(engine_journal):
                if not entered.wait(3):raise RuntimeError('Conversation tool never ran')
                engine_journal.record('one-r0','independent_engine_fixture',{'saved':True})
                saved.set()
            try:
                with mock.patch('arena.api_providers.APIProvider.respond',new=response):
                    prepare([('one-r0',model)],value,root,journal,BlockingTool(),on_progress=engine_progress,independent_fights=True)
                self.assertTrue(saved.is_set())
                self.assertEqual(journal.state('one-r0')['status'],'submitted')
                journal.verify()
            finally:journal.db.close()

    def test_committed_submissions_are_seen_without_a_conversation_callback(self):
        value=config();model=value['models'][0];observed=threading.Event();scanning=threading.Event()
        with scratch_directory() as root:
            journal=Journal(root)
            journal.save('one-r0',initial_state('one-r0',model,value),'session_created')
            def evaluate(engine,config,out,engine_journal,generation):
                self.assertEqual(generation,0)
                if engine_journal.metadata()['one-r0'].get('submission'):observed.set()
            try:
                with mock.patch('arena.greedy.evaluate',side_effect=evaluate):
                    with FightCoordinator(root,value,CoordinatorEngine(),lambda _:scanning.set()):
                        self.assertTrue(scanning.wait(3))
                        state=journal.state('one-r0');state.update(status='submitted',submission={'entrypoint':'main.leek'})
                        journal.save('one-r0',state,'finished')
                        self.assertTrue(observed.wait(3))
                journal.verify()
            finally:journal.db.close()
