"""Local credentials load on startup without shell execution or secret diagnostics."""
import unittest
from arena.core import ArenaError, scratch_directory
from arena.environment import load_dotenv


class EnvironmentTests(unittest.TestCase):
    def test_credentials_quotes_comments_and_existing_environment(self):
        with scratch_directory() as root:
            path=root/'.env'
            path.write_text('\ufeff# local keys\nARENA_ONE=first\nARENA_ONE=last\n'
                            'export ARENA_TWO="key # literal $VALUE $(command)" # comment\n'
                            "ARENA_THREE='C:\\literal'\nARENA_FOUR=value # comment\n",encoding='utf-8')
            env={'ARENA_ONE':'process-value'}
            load_dotenv(path,env)
            self.assertEqual(env,{'ARENA_ONE':'process-value','ARENA_TWO':'key # literal $VALUE $(command)',
                                  'ARENA_THREE':'C:\\literal','ARENA_FOUR':'value'})

    def test_missing_file_and_atomic_errors_do_not_disclose_values(self):
        with scratch_directory() as root:
            path=root/'.env';env={}
            load_dotenv(path,env)
            path.write_text('ARENA_ONE=secret\nARENA_TWO="private-unclosed\n',encoding='utf-8')
            with self.assertRaisesRegex(ArenaError,r'line 2$') as raised:
                load_dotenv(path,env)
            self.assertNotIn('private',str(raised.exception))
            self.assertEqual(env,{})
