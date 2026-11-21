"""Offline continuation fixtures; no live host, scheduled task, model or GPU."""
import ast
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from tests.fixture_retention import FixtureDirectory
from tests.test_collector_narrator_batch_update import helper,create_database,EXPECTED
from youtube_ops import collector_narration_common as common
from youtube_ops import collector_narrator_recovery_probe as probe

SOURCE=Path(__file__).resolve().parents[1]/'docs/collector/host-tools/Resume-KnowledgeNetworkNarratorBatchOffline.ps1'


def driver():
    source=SOURCE.read_text().split("$driver=@'\n",1)[1].split("\n'@",1)[0]
    tree=ast.parse(source)
    nodes=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))
           or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='OFFLINE_TASK' for target in node.targets)]
    ns={'__name__':'owned_offline_fixture','STEM':'owned-offline','WORK':Path('unused')}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'owned-offline-fixture','exec'),ns)
    return ns,source


class OfflineContinuationTests(unittest.TestCase):
    def setUp(self):
        self.folder=FixtureDirectory(prefix='kn-offline-unit-');self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);(self.root/'code').mkdir();(self.root/'data').mkdir();(self.root/'work').mkdir()
        self.xml='<Task>\r\n<Settings>original</Settings>\r\n</Task>'
        (self.root/'code/task.private.xml').write_bytes(self.xml.encode())
        self.config={'owner_sid':'S-1-5-21-1-2-3-1001'}
        self.code,self.source=driver();self.code['WORK']=self.root/'work'
        self.value={'xml':self.xml,'owner_sid':self.config['owner_sid'],'state':3,'enabled':True,'instances':0,'listeners':[],
                    'canonical_processes':[],'logon':3,'runlevel':0,'actions':1,'triggers':0,'multiple':2,'hard_terminate':False,
                    'execution_limit':'PT0S','execute':str(self.root/'python.exe'),'working_directory':str(self.root/'code'),
                    'arguments':'-I -S -B '+str(self.root/'code/narrator-standalone.py').replace('\\','/')}
        self.ns={'ROOT':self.root,'WORK':self.root/'work','DATA':self.root/'data','PYTHON':self.root/'python.exe',
                 'ps':lambda code:copy.deepcopy(self.value),'write':Mock()}

    def test_original_xml_bytes_and_exact_ready_disabled_semantics(self):
        self.assertEqual(self.code['offline_proof'](self.ns,self.config),self.value)
        self.value['xml']=self.xml.replace('\r\n','\n')
        with self.assertRaisesRegex(RuntimeError,'exact_offline'):self.code['offline_proof'](self.ns,self.config)
        self.value.update(xml='disabled XML',state=1,enabled=False)
        self.assertEqual(self.code['offline_proof'](self.ns,self.config,False,'disabled XML'),self.value)
        with self.assertRaisesRegex(RuntimeError,'disabled_task_xml_required'):self.code['offline_proof'](self.ns,self.config,False)
        self.assertTrue(self.ns['write'].called,'Actual metadata must be retained even before a comparison fails')

    def test_every_busy_or_untrusted_task_condition_blocks(self):
        for edit in ({'state':4},{'enabled':False},{'instances':1},{'listeners':[{'port':39110}]},
                     {'canonical_processes':[{'pid':123}]},{'owner_sid':'other'},{'runlevel':1},{'logon':5},
                     {'triggers':1},{'actions':2},{'multiple':0},{'hard_terminate':True},{'execute':'other.exe'},
                     {'arguments':'changed'},{'working_directory':'other'}):
            with self.subTest(edit=edit):
                self.ns['ps']=lambda code,edit=edit:{**self.value,**edit}
                with self.assertRaisesRegex(RuntimeError,'exact_offline'):self.code['offline_proof'](self.ns,self.config)

    def test_capture_only_preserves_original_prepared_and_diagnostic_files(self):
        (self.ns['WORK']/'update-helper.py').write_text('retained original')
        (self.ns['WORK']/'batch-preflight-owned.report.private.json').write_text('{}')
        self.code['capture_only'](self.ns)
        (self.ns['WORK']/'old-code').mkdir()
        with self.assertRaisesRegex(RuntimeError,'prior_activity'):self.code['capture_only'](self.ns)
        self.assertEqual((self.ns['WORK']/'update-helper.py').read_text(),'retained original')

    def test_mutation_order_and_original_namespace_guards_survive_start(self):
        tree=ast.parse(self.source);main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        text=ast.get_source_segment(self.source,main)
        self.assertLess(text.index('with existing_lease'),text.index("connection=ns['Sqlite']"))
        self.assertLess(text.index("NamespaceGuard(ns['DB'])"),text.index("connection=ns['Sqlite']"))
        self.assertLess(text.index("offline_proof(ns,config,False,disabled['xml'])"),text.index("connection=ns['Sqlite']"))
        self.assertLess(text.index('gpu_baseline(ns,review)'),text.index("ns['parity_task'](config)"))
        self.assertLess(text.index("ns['parity_task'](config)"),text.index('segment_batches=True'))
        self.assertLess(text.index("ns['task_operation']('start'"),text.index("ns['bind_running'](db_guard.native"))
        self.assertIn("if db_guard:db_guard.close()",text);self.assertIn("if lock_guard:lock_guard.close()",text)
        self.assertIn("post-start-task-raw.private.json",text)
        self.assertNotIn('TerminateProcess',self.source);self.assertNotIn('live_ledger_handles',self.source)
        self.assertNotIn("ns['main']",self.source)
        self.assertIn('PREPARED_MANUAL_ROLLBACK_NOT_TESTED',self.source)

    def test_optional_gpu_unavailable_or_changed_never_executes_and_query_errors_are_retained(self):
        run=Mock();self.code['GPU']=Path('fixed-nvidia.exe');self.code['GPU_PIN']='expected'
        self.code['subprocess']=SimpleNamespace(run=run,PIPE=-1,CREATE_NO_WINDOW=0,TimeoutExpired=subprocess.TimeoutExpired)
        record=Mock();ns={'write':record,'raw_write':Mock(),'sha':lambda path:'expected'}
        self.code['GPU_EVIDENCE']={'status':'UNAVAILABLE','reason':'signature_unavailable'}
        self.code['gpu_baseline'](ns,self.root);run.assert_not_called()
        self.assertEqual(record.call_args.args[1]['status'],'UNAVAILABLE')
        self.code['GPU_EVIDENCE']={'status':'VERIFIED'};ns['sha']=lambda path:'changed'
        self.code['gpu_baseline'](ns,self.root);run.assert_not_called()
        ns['sha']=lambda path:'expected';run.side_effect=subprocess.TimeoutExpired('owned-query',20,stderr=b'private failure')
        self.code['gpu_baseline'](ns,self.root)
        self.assertEqual(record.call_args.args[1]['status'],'UNAVAILABLE')
        self.assertTrue(record.call_args.args[1]['tool_executed'])
        self.assertEqual(ns['raw_write'].call_args.args[1],b'private failure')
        run.side_effect=OSError('tool failed to start')
        self.code['gpu_baseline'](ns,self.root)
        self.assertFalse(record.call_args.args[1]['tool_executed'])
        run.side_effect=None;run.return_value=SimpleNamespace(stdout=b'GPU facts',stderr=b'',returncode=0)
        self.code['gpu_baseline'](ns,self.root)
        self.assertEqual(record.call_args.args[1]['status'],'AVAILABLE')
        # Evidence-write failures remain fatal; only the optional tool is skipped.
        record.side_effect=OSError('evidence unavailable')
        with self.assertRaises(OSError):self.code['gpu_baseline'](ns,self.root)

    def test_fixed_scope_and_gpu_facts_do_not_claim_unrelated_activity(self):
        text=SOURCE.read_text()
        for forbidden in ('Remove-Item','Stop-ScheduledTask','Start-Service','tailscale','Set-ExecutionPolicy','--gpu-reset'):
            self.assertNotIn(forbidden,text)
        self.assertIn("GPU=Path('C:/Windows/System32/nvidia-smi.exe')",self.source)
        self.assertIn("facts_only=True,unrelated_workloads_changed=False",self.source)
        self.assertIn("$start.Arguments='-I -S -B -'",text)


@unittest.skipUnless(os.name=='nt' and os.environ.get('COLLECTOR_NATIVE_BATCH_OFFLINE')=='1','Opt-in isolated Windows lease/namespace/CAPI fixtures; no host or GPU')
class NativeOfflineTests(unittest.TestCase):
    def test_native_parser(self):
        code="$e=$null;$t=$null;$null=[Management.Automation.Language.Parser]::ParseFile([Console]::In.ReadToEnd(),[ref]$t,[ref]$e);if($e.Count){$e|Out-String;exit 1};'PARSE_PASS'"
        result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],input=str(SOURCE),capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_held_lease_without_listener_and_lock_replacement_are_denied(self):
        functions,_=driver()
        with FixtureDirectory(prefix='kn-offline-lease-',trusted_execution=True) as folder:
            folder=Path(folder);lock=folder/'remote-voice.lock';lock.write_bytes(b'0')
            ns={'DATA':folder,'Sqlite':Mock()}
            reservation=functions['reserve_port'](0)
            try:
                self.assertEqual(reservation.getsockopt(functions['socket'].SOL_SOCKET,functions['socket'].SO_ACCEPTCONN),0)
                with probe.NamespaceGuard(lock) as guard,common.voice_lease(folder):
                    with self.assertRaises(common.VoiceError):
                        with functions['existing_lease'](ns,{'voice_lease':common.voice_lease},guard):ns['Sqlite']()
                    ns['Sqlite'].assert_not_called()
                    with self.assertRaises(OSError):lock.rename(folder/'retained-lock-attempt')
            finally:reservation.close()
        with FixtureDirectory(prefix='kn-offline-replaced-',trusted_execution=True) as folder:
            folder=Path(folder);original=folder/'original-lock';original.write_bytes(b'0');(folder/'remote-voice.lock').hardlink_to(original)
            with self.assertRaises(probe.ProbeBlocked):probe.NamespaceGuard(folder/'remote-voice.lock')

    def test_wrong_physical_ledger_and_active_writer_block(self):
        functions,_=helper()
        with FixtureDirectory(prefix='kn-offline-sqlite-',trusted_execution=True) as folder:
            folder=Path(folder);path=folder/'host-narrations.sqlite';wrong=folder/'wrong.sqlite';create_database(path);create_database(wrong)
            with probe.NamespaceGuard(path) as guard:
                with self.assertRaisesRegex(RuntimeError,'sqlite_ledger_mismatch'):functions['Sqlite'](wrong,guard)
                connection=functions['Sqlite'](path,guard)
                try:
                    with closing(sqlite3.connect(path,isolation_level=None)) as writer:
                        writer.execute('BEGIN IMMEDIATE');backups=[]
                        with self.assertRaisesRegex(RuntimeError,'sqlite_busy_or_failed'):functions['prepare_fence'](connection,EXPECTED,lambda:backups.append(True))
                        self.assertEqual(backups,[]);writer.rollback()
                finally:connection.close()


if __name__=='__main__':unittest.main()
