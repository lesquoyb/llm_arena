import copy
import unittest
from arena.core import ArenaError,ROOT,read_json,scratch_directory
from arena.experiment import validate_config
from arena.api_providers import APIProvider
from arena_web.data import Store


def sized_model():
    return {'id':'local','provider':'openai-compatible','model':'local-model',
            'endpoint':'http://localhost:11434/v1/chat/completions','api_key_env':'ARENA_SIZE',
            'model_size_billion':7.5,'pricing':{'currency':'USD','date':'2026-10-28','input_per_million':'0','output_per_million':'0'}}


class ModelSizeTests(unittest.TestCase):
    def test_optional_size_is_validated_without_becoming_a_generation_parameter(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        model=sized_model();config.update(models=[model],spending={'allow_paid_calls':True})
        validate_config(config)
        without={key:value for key,value in model.items() if key!='model_size_billion'}
        history=[{'role':'user','content':'Write a strategy.'}]
        self.assertEqual(APIProvider(model).payload(history,[],16),APIProvider(without).payload(history,[],16))
        for invalid in (0,-1,True,'7B',None,float('nan'),float('inf'),10**1000):
            value=copy.deepcopy(config);value['models'][0]['model_size_billion']=invalid
            with self.subTest(invalid_type=type(invalid).__name__),self.assertRaisesRegex(ArenaError,'Model size'):
                validate_config(value)
        config['models']=[without];validate_config(config)

    def test_historical_size_annotation_requires_same_profile_model_and_endpoint_and_never_overwrites_saved_size(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');model=sized_model();store.save_participant(model)
            historical={key:value for key,value in model.items() if key!='model_size_billion'}
            self.assertEqual(store.model_size(historical),7.5)
            self.assertEqual(store.model_size({**model,'model_size_billion':3}),3)
            for key,value in [('model','other'),('endpoint','http://localhost:11435/v1/chat/completions'),('id','other'),('provider','openai')]:
                self.assertIsNone(store.model_size({**historical,key:value}))
            self.assertNotIn('model_size_billion',historical)
