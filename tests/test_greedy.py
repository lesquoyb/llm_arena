import unittest
from pathlib import Path
from unittest import mock
from arena.core import scratch_directory
from arena.greedy import evaluate
from arena.evolution import references


class GreedyTests(unittest.TestCase):
    def test_only_frozen_current_round_sources_enter_append_only_tournament(self):
        journal=mock.Mock()
        journal.states.return_value={
            'initial':{'generation':0,'model':'one','replicate':0,'submission':{'entrypoint':'main.leek'}},
            'ready':{'generation':1,'parent':'initial','model':'one','replicate':0,'submission':{'entrypoint':'main.leek'}},
            'editing':{'generation':1,'model':'one','replicate':0,'status':'running'}}
        config={'name':'test','seeds':[101],'final_seeds':[301],'scenario':{},'include_mirrors':True}
        with mock.patch('arena.greedy.run_tournament',return_value={'completed':1}) as tournament:
            evaluate(mock.Mock(),config,Path('/unused'),journal,1)
            manifest=tournament.call_args.args[1]
            self.assertEqual([s['id'] for s in manifest['strategies']],['ready'])
            self.assertEqual(manifest['strategies'][0]['parent'],'initial')
            self.assertEqual(manifest['seeds'],[301])
            self.assertTrue(tournament.call_args.kwargs['allow_extend'])
        config['include_mirrors']=False
        with mock.patch('arena.greedy.run_tournament') as tournament:
            self.assertIsNone(evaluate(mock.Mock(),config,Path('/unused'),journal,1))
            tournament.assert_not_called()

    def test_incremental_reference_results_keep_earlier_entrants(self):
        with scratch_directory() as tmp:
            engine=mock.Mock()
            engine.fight.return_value={'status':'failed'}
            journal=mock.Mock()
            journal.state.return_value={}
            opponent={'id':'fixed','path':tmp/'fixed','submission':{'entrypoint':'main.leek'}}
            def entrant(name):return {'id':name,'path':tmp/name,'submission':{'entrypoint':'main.leek'}}
            config={'final_seeds':[301],'scenario':{}}
            first=references(engine,config,tmp,journal,[entrant('one')],'g1-panel',[opponent],incremental=True)
            second=references(engine,config,tmp,journal,[entrant('two')],'g1-panel',[opponent],incremental=True)
            self.assertEqual(len(first),2)
            self.assertEqual(len(second),4)
            self.assertTrue(first.keys() <= second.keys())
            self.assertEqual({row['session'] for row in second.values()},{'one','two'})
