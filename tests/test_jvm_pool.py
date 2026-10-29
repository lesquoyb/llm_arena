"""Persistent JVM transport resets application statics and replaces dead slots."""
import shutil
import tempfile
import unittest
from pathlib import Path
from arena.core import ROOT
from arena.engine import Engine
from arena.jvm_pool import Pool
import subprocess


@unittest.skipUnless(shutil.which('java') and shutil.which('javac'),'JDK required')
class JVMTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        classes=cls.root/'classes';classes.mkdir()
        source=cls.root/'ArenaMain.java'
        source.write_text('''package arena.bridge;
import java.nio.file.*;
public class ArenaMain {
 static int counter=0;
 public static void main(String[] args) throws Exception {
  if(Files.readString(Path.of("strategies/1/main.leek")).equals("sleep"))Thread.sleep(10000);
  Files.writeString(Path.of(args[2]),"{\\\"success\\\":true,\\\"winner\\\":-1,\\\"duration\\\":1,\\\"fight\\\":{\\\"counter\\\":"+(++counter)+"},\\\"team_metrics\\\":{}}");
 }
}''',encoding='utf-8')
        subprocess.run([shutil.which('javac'),'-d',str(classes),str(ROOT/'engine/ArenaWorker.java'),str(source)],check=True,capture_output=True)
        (cls.root/'data').mkdir()

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def engine(self):
        engine=object.__new__(Engine)
        engine.metadata={'data':str(self.root/'data'),'java':shutil.which('java'),'classes':str(self.root/'classes'),'jar':str(self.root/'unused.jar')}
        engine.worker_options=[];engine.backend='process';engine.timeout=5
        engine._jvm_pool=Pool(engine,recycle=2)
        self.addCleanup(engine.close)
        return engine

    def invoke(self,engine,root,content='ok'):
        (root/'strategies/1').mkdir(parents=True)
        (root/'strategies/1/main.leek').write_text(content,encoding='utf-8')
        (root/'scenario.json').write_text('{}',encoding='utf-8')
        return engine.invoke(root,'fight','scenario.json')

    def test_reuse_resets_statics_and_recycles_process(self):
        engine=self.engine()
        with tempfile.TemporaryDirectory() as directory:
            values=[self.invoke(engine,Path(directory)/str(i)) for i in range(3)]
        self.assertTrue(all(value['status']=='completed' for value in values))
        self.assertEqual(len({value['replay_sha256'] for value in values}),1)
        self.assertEqual(values[0]['timings']['jvm_pid'],values[1]['timings']['jvm_pid'])
        self.assertNotEqual(values[1]['timings']['jvm_pid'],values[2]['timings']['jvm_pid'])

    def test_timeout_destroys_only_its_slot_and_next_request_succeeds(self):
        engine=self.engine();engine.timeout=1
        with tempfile.TemporaryDirectory() as directory:
            stopped=self.invoke(engine,Path(directory)/'stopped','sleep')
            engine.timeout=5
            recovered=self.invoke(engine,Path(directory)/'recovered')
        self.assertEqual(stopped['status'],'timeout')
        self.assertEqual(recovered['status'],'completed')
        self.assertFalse(recovered['timings']['jvm_reused'])
