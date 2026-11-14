"""Editor bridge source tests with simulated native calls, never live editor acceptance."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from youtube_ops.collector_editor import OpenShot, EditorError
from youtube_ops.collector_editor_job import execute, from_environment, _new
from youtube_ops.collector_companion import run_once

JOB, SESSION = 'a'*32, 'b'*32
COMMANDS = [{'method':'text.add','params':{'text':'Private caption','layer':4000000,'position':0,'duration':1},'as':'title'}]

class EditorJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.vault=self.root/'vault'; self.vault.mkdir()
        exe=self.root/'openshot-qt-cmd.exe'; exe.write_bytes(b'unit fixture executable never launched')
        self.client=OpenShot(exe,hashlib.sha256(exe.read_bytes()).hexdigest(),self.vault,SESSION)
        (self.client.receipts/('session-'+SESSION+'.json')).write_text(json.dumps({
            'session_id':SESSION,'executable_sha256':self.client.executable_sha256,'font_directory':str(self.client.font_directory)}))
        self.revision=3
        self.client.inspect=Mock(side_effect=lambda:{'revision':self.revision,'data':{'private':'project caption/path context'}})
        self.client.apply=Mock(side_effect=self.apply)
        self.client.save=Mock(side_effect=self.save)
        self.client.reopen=Mock(side_effect=self.reopen)
        self.cancel=threading.Event()
    def apply(self,commands,base_revision):
        self.assertEqual(base_revision,self.revision); self.revision+=1
        return {'revision':self.revision,'refs':{'title':{'clip':{'id':'CLIP'}}}}
    def save(self,path):
        Path(path).write_bytes(b'saved native fixture')
        self.revision+=2
        return {'native':{'revision':self.revision},'path':path,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    def reopen(self,path,sha256):
        self.revision+=1
        return {'revision':self.revision}
    def run_job(self,operation='inspect',request=None,job=JOB):
        return execute(job,{'session_id':SESSION,'operation':operation,'request':request or {}},self.cancel,lambda session:self.client)
    def test_inspect_durable_receipt_has_actual_context_no_private_result(self):
        result=self.run_job()
        self.assertEqual(result['status'],'completed'); self.assertEqual(result['revision'],3)
        path=self.client.receipts/('service-'+JOB+'.json')
        self.assertEqual(result['native_receipt_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        receipt=json.loads(path.read_bytes())
        self.assertEqual(receipt['job_id'],JOB); self.assertEqual(receipt['session_id'],SESSION)
        self.assertEqual(receipt['before'],receipt['after']); self.assertEqual(receipt['operation'],'inspect')
        self.assertNotIn('caption/path',json.dumps(result)); self.assertNotIn('narrator_id',result)
        self.client.apply.assert_not_called()
    def test_apply_uses_same_commands_and_actual_post_revision(self):
        result=self.run_job('apply',{'commands':COMMANDS,'base_revision':3})
        self.assertEqual(result['status'],'completed'); self.assertEqual(result['revision'],4)
        self.client.apply.assert_called_once_with(COMMANDS,3)
    def test_stale_revision_blocked_before_dispatch_and_intent(self):
        result=self.run_job('apply',{'commands':COMMANDS,'base_revision':2})
        self.assertEqual(result['error'],'EDITOR_REVISION_CONFLICT'); self.client.apply.assert_not_called()
        self.assertFalse((self.client.receipts/('service-'+JOB+'-intent.json')).exists())
    def test_unsupported_method_never_dispatches(self):
        self.assertEqual(self.run_job('apply',{'commands':[{'method':'shell.run','params':{}}],'base_revision':3})['status'],'failed')
        self.client.inspect.assert_not_called(); self.client.apply.assert_not_called()
    def test_save_uses_actual_after_revision_even_native_save_relocates(self):
        result=self.run_job('save',{'path':str(self.vault/'new.osp')})
        self.assertEqual(result['status'],'completed'); self.assertEqual(result['revision'],5)
    def test_edit_after_save_reply_cannot_be_attributed_to_saved_project(self):
        def raced_save(path):
            result=self.save(path)
            self.revision+=1
            return result
        self.client.save.side_effect=raced_save
        result=self.run_job('save',{'path':str(self.vault/'race.osp')})
        self.assertEqual(result['error'],'EDITOR_REVISION_CHANGED_RECONCILE_REQUIRED')
        self.assertEqual(result['status'],'reconciliation_required')
        self.assertTrue((self.client.receipts/('service-'+JOB+'-intent.json')).exists())
        self.assertFalse((self.client.receipts/('service-'+JOB+'.json')).exists())
    def test_reopen_binds_path_hash_and_actual_revision(self):
        path=self.vault/'owned.osp'; path.write_bytes(b'fixture')
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(self.run_job('reopen',{'path':str(path),'sha256':sha})['revision'],4)
        self.client.reopen.assert_called_once_with(str(path),sha)
    def test_outside_vault_or_unc_save_denied_without_native_call(self):
        for path in (str(self.root/'escape.osp'),r'\\untrusted\share\escape.osp'):
            with self.subTest(path=path):
                self.assertIn(self.run_job('save',{'path':path})['status'],('failed','blocked'))
        self.client.save.assert_not_called(); self.client.inspect.assert_not_called()
    def test_reparse_import_denied_before_native_dispatch(self):
        media=self.vault/'owned.wav'; media.write_bytes(b'fixture')
        link=self.vault/'linked.wav'
        try: os.symlink(media,link)
        except OSError: self.skipTest('OS did not permit local symlink fixture')
        result=self.run_job('apply',{'commands':[{'method':'file.import','params':{'path':str(link)}}],'base_revision':3})
        self.assertEqual(result['error'],'EDITOR_REPARSE_POINT_DENIED'); self.client.apply.assert_not_called()
    def test_broken_output_symlink_denied_before_dispatch(self):
        link=self.vault/'broken.osp'
        try: os.symlink(self.vault/'missing.osp',link)
        except OSError: self.skipTest('OS did not permit local symlink fixture')
        self.assertEqual(self.run_job('save',{'path':str(link)})['error'],'EDITOR_REPARSE_POINT_DENIED')
        self.client.inspect.assert_not_called(); self.client.save.assert_not_called()
    def test_timeout_after_dispatch_keeps_intent_never_replays(self):
        self.client.apply.side_effect=EditorError('native_timeout_reconcile_required')
        request={'commands':COMMANDS,'base_revision':3}
        self.assertEqual(self.run_job('apply',request)['status'],'reconciliation_required')
        self.assertEqual(self.run_job('apply',request)['error'],'EDITOR_JOB_ALREADY_RECORDED')
        self.client.apply.assert_called_once()
    def test_completed_receipt_never_overwritten(self):
        self.run_job(); path=self.client.receipts/('service-'+JOB+'.json'); raw=path.read_bytes()
        self.assertEqual(self.run_job()['status'],'reconciliation_required'); self.assertEqual(path.read_bytes(),raw)
    def test_outcome_write_failure_retains_intent_and_requires_reconciliation(self):
        def persist(path,value):
            if path.name.endswith('-intent.json'): return _new(path,value)
            raise OSError('private path error')
        with patch('youtube_ops.collector_editor_job._new',side_effect=persist):
            result=self.run_job('apply',{'commands':COMMANDS,'base_revision':3})
        self.assertEqual(result['status'],'reconciliation_required'); self.client.apply.assert_called_once()
        self.assertTrue((self.client.receipts/('service-'+JOB+'-intent.json')).exists())
        self.assertNotIn('private path',json.dumps(result))
    def test_existing_saved_project_cannot_be_overwritten(self):
        path=self.vault/'preserved.osp'; path.write_bytes(b'existing approved project')
        self.assertEqual(self.run_job('save',{'path':str(path)})['status'],'failed')
        self.assertEqual(path.read_bytes(),b'existing approved project'); self.client.save.assert_not_called()
    def test_readback_revision_race_is_reconciliation(self):
        self.client.apply.side_effect=lambda *args:{'revision':9}
        self.assertEqual(self.run_job('apply',{'commands':COMMANDS,'base_revision':3})['status'],'reconciliation_required')
    def test_cancel_before_dispatch_does_not_inspect_or_mutate(self):
        self.cancel.set(); self.assertEqual(self.run_job()['status'],'cancelled')
        self.client.inspect.assert_not_called()
    def test_cancel_after_dispatch_is_not_false_undo(self):
        def apply(*args):
            self.cancel.set(); self.revision+=1; return {'revision':self.revision}
        self.client.apply.side_effect=apply
        self.assertEqual(self.run_job('apply',{'commands':COMMANDS,'base_revision':3})['status'],'reconciliation_required')
        self.assertFalse((self.client.receipts/('service-'+JOB+'.json')).exists())
    def test_wrong_managed_session_denied(self):
        self.client.session='c'*32
        self.assertEqual(self.run_job()['error'],'EDITOR_SESSION_MISMATCH'); self.client.inspect.assert_not_called()
    def test_missing_configuration_blocks_without_native_launch(self):
        with patch.dict(os.environ,{},clear=True),patch('youtube_ops.collector_editor_job.OpenShot') as native:
            result=execute(JOB,{'session_id':SESSION,'operation':'inspect','request':{}},self.cancel)
            self.assertEqual(result['status'],'blocked'); native.assert_not_called()
    def test_malformed_operation_does_not_echo_private_payload(self):
        result=self.run_job({'private':'private host path'})
        self.assertEqual(result['operation'],'invalid'); self.assertNotIn('private host',json.dumps(result))

class CompanionEditorTests(unittest.TestCase):
    def service(self):
        service=Mock()
        def call(op,body=None):
            if op=='claim': return {'job':{'job_id':JOB,'job_type':'editor.operation'},'inputs':{'session_id':SESSION,'operation':'inspect','request':{}},'lease_token':'c'*32}
            if op=='heartbeat': return {'cancel_requested':False}
            return {'job_id':JOB,'state':'succeeded' if body['result']['status']=='completed' else body['result']['status']}
        service.call.side_effect=call
        return service
    def test_dispatch_editor_without_voice_factory(self):
        voice=Mock(); executor=Mock(return_value={'status':'completed','provider':'openshot_native','publication_eligible':False,'operation':'inspect','revision':3,'native_receipt_sha256':'d'*64})
        result=run_once(self.service(),voice,editor_executor=executor)
        self.assertEqual(result['provider'],'openshot_native'); self.assertNotIn('narrator_id',result)
        executor.assert_called_once(); voice.assert_not_called()
    def test_editor_unknown_failure_keeps_typed_reconcile_envelope(self):
        result=run_once(self.service(),editor_executor=Mock(side_effect=RuntimeError('private project path')))
        self.assertEqual(result['status'],'reconciliation_required'); self.assertEqual(result['provider'],'openshot_native')
        self.assertNotIn('narrator_id',result); self.assertNotIn('private',json.dumps(result))
    def test_editor_lost_lease_keeps_typed_reconcile_envelope(self):
        service=self.service(); original=service.call.side_effect
        def call(op,body=None):
            if op=='heartbeat': raise RuntimeError('lost')
            return original(op,body)
        service.call.side_effect=call
        def executor(job,inputs,cancel):
            self.assertTrue(cancel.wait(1))
            return {'status':'cancelled','provider':'openshot_native','publication_eligible':False,'operation':'inspect'}
        result=run_once(service,heartbeat_seconds=.01,editor_executor=executor)
        self.assertEqual(result['error'],'COMPANION_LEASE_LOST'); self.assertEqual(result['provider'],'openshot_native')

if __name__=='__main__': unittest.main()
