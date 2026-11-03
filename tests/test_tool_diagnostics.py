"""A locked writer is observable; WAL readers and indexed lineage stay usable."""
import sqlite3
import unittest
from unittest import mock
from arena.core import scratch_directory,read_json
from arena.experiment import Journal,execute_tool
from arena.sqlite_metrics import connect,collect
from arena.submitted_versions import OwnSubmissions


class ToolDiagnosticsTests(unittest.TestCase):
    def test_competing_writer_wait_is_measured_and_wal_reader_is_not_blocked(self):
        with scratch_directory() as root:
            first=connect(root/'test.sqlite');second=connect(root/'test.sqlite',timeout=.05)
            try:
                first.execute('PRAGMA journal_mode=WAL')
                first.execute('CREATE TABLE values_table(value INTEGER)');first.commit()
                first.execute('BEGIN IMMEDIATE');first.execute('INSERT INTO values_table VALUES (1)')
                with collect() as stats:
                    self.assertEqual(second.execute('SELECT COUNT(*) FROM values_table').fetchone()[0],0)
                    with self.assertRaisesRegex(sqlite3.OperationalError,'locked'):
                        second.execute('INSERT INTO values_table VALUES (2)')
                self.assertEqual(stats['sqlite_errors'],1)
                self.assertGreaterEqual(stats['sqlite_wall_seconds'],.03)
                self.assertLess(stats['sqlite_cpu_seconds'],stats['sqlite_wall_seconds'])
            finally:first.rollback();second.close();first.close()

    def test_lineage_uses_small_index_without_reading_conversation_state(self):
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                journal.save('parent',{'model':'m','replicate':0,'generation':0,'submission':{'entrypoint':'main.leek','files':{}},'history':[]},'finished')
                def indexed(*args,**kwargs):
                    db=connect(*args,**kwargs)
                    db.set_authorizer(lambda action,table,column,*rest:sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and table=='sessions' and column=='state' else sqlite3.SQLITE_OK)
                    return db
                with mock.patch('arena.sqlite_metrics.connect',side_effect=indexed):
                    rows=OwnSubmissions(root,{'model':'m','replicate':0,'generation':1,'parent':'parent'}).versions()
                self.assertEqual(rows[0]['session'],'parent')
            finally:journal.db.close()

    def test_tool_receipt_records_execution_and_publication_separately(self):
        from test_parallel_requests import config
        from arena.experiment import initial_state
        with scratch_directory() as root:
            value=config();journal=Journal(root);tools=mock.Mock();tools.workspace=root/'workspace';tools.workspace.mkdir()
            tools.call.return_value={'matches':[]}
            state=initial_state('one-r0',value['models'][0],value)
            journal.save('one-r0',state,'session_created')
            try:
                result=execute_tool('one-r0',state,tools,journal,{'name':'list_past_fights','arguments':{}},'call-1-tool-0',{})
                trace=read_json(root/'sessions/one-r0/tool-progress.json')
                self.assertEqual(trace['phase'],'completed')
                self.assertIn('executing_seconds',trace['timings'])
                self.assertIn('publishing_result_seconds',trace['timings'])
                self.assertGreater(trace['timings']['sqlite_calls'],0)
                self.assertEqual(result,{'matches':[]})
                journal.verify()
            finally:journal.db.close()
