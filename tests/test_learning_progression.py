"""Historical strength uses candidate outcomes and an explicit opponent cohort."""
import unittest
from arena_web.progression import summarize


class LearningProgressionTests(unittest.TestCase):
    def test_root_parent_pool_are_distinct_and_repetitions_are_paired(self):
        models={'a':{'provider':'openai-compatible'},'b':{'provider':'gemini'},'fixed':{'provider':'mock'}}
        states={
            'a0':{'model':'a','generation':0,'replicate':0},
            'a0-other':{'model':'a','generation':0,'replicate':1},
            'b0':{'model':'b','generation':0,'replicate':0},
            'a1-f':{'model':'a','generation':1,'condition':'feedback','replicate':0,'parent':'a0'},
            'a1-c':{'model':'a','generation':1,'condition':'control','replicate':0,'parent':'a0'},
            'b1-f':{'model':'b','generation':1,'condition':'feedback','replicate':0,'parent':'b0'},
            'a2-f':{'model':'a','generation':2,'condition':'feedback','replicate':0,'parent':'a1-f'},
            'fixed':{'model':'fixed','generation':1,'condition':'feedback'}}
        def fight(path,candidate,opponent,winner,side=0,status='completed'):
            return {'path':path,'kind':'evaluation' if opponent in {'a0','a0-other','b0'} else 'progression',
                    'candidate':candidate,'candidate_side':side,'sides':[candidate,opponent] if side==0 else [opponent,candidate],
                    'seed':101,'result':{'status':status,'winner_side':winner}}
        matches=[fight('initial','a2-f','a0',1,side=1),fight('parent','a2-f','a1-f',1),
                 fight('other-track','a2-f','a1-c',0),fight('other-model','a2-f','b1-f',-1,side=1),
                 fight('other-repeat','a2-f','a0-other',0),fight('reference','a2-f','fixed',0),
                 fight('engine-error','a2-f','a1-f',None,status='failed'),
                 fight('r2-self','a1-f','a0',0),fight('r2-other','a1-f','b0',-1)]
        matches.append(matches[1].copy())
        rows=summarize(states,models,matches)
        final=next(row for row in rows if row['model']=='a' and row['generation']==2)
        self.assertEqual(final['own_initial']['score'],1)
        self.assertEqual(final['own_initial']['completed'],1)
        self.assertEqual(final['own_previous']['score'],0)
        self.assertEqual(final['own_previous']['completed'],1)
        self.assertEqual(final['own_previous']['failures'],1)
        self.assertEqual(final['previous_pool']['score'],.5)
        self.assertEqual(final['previous_pool']['completed'],3)
        self.assertEqual(final['previous_pool']['opponent_versions'],3)
        earlier=next(row for row in rows if row['model']=='a' and row['generation']==1 and row['condition']=='feedback')
        self.assertEqual(earlier['own_previous']['score'],1)
        self.assertEqual(earlier['previous_pool']['score'],.75)
        empty=next(row for row in rows if row['model']=='a' and row['condition']=='control')
        self.assertIsNone(empty['own_initial']['score'])
        self.assertFalse(any(row['model']=='fixed' for row in rows))
