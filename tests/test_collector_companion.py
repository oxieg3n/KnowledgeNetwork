"""Mock service/provider tests only; no live host or installed-service acceptance."""
from tests.fixture_retention import FixtureDirectory
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import wave
from youtube_ops.collector_companion import CompanionError, ServiceCLI, main, run_once
from youtube_ops.collector_narration_common import VoiceError, inspect_wav
from youtube_ops.collector_narrator_host import NarratorError

JOB, TOKEN, TEXT = 'a'*32, 'b'*32, 'Actual measured segment.'

class Service:
    def __init__(self):
        self.calls=[]
        self.heartbeat={'cancel_requested':False}
        self.type='narration.generate'
        self.text=TEXT
        self.idle=False
        self.complete_error=False
        self.wrong_complete=False
    def call(self, op, body=None):
        self.calls.append((op,body))
        if op=='claim':
            if self.idle: return dict(job=None,inputs=None,lease_token=None)
            return dict(job={'job_id':JOB,'job_type':self.type},inputs={'text':self.text},lease_token=TOKEN)
        if op=='heartbeat':
            if isinstance(self.heartbeat,Exception): raise self.heartbeat
            return self.heartbeat
        if self.complete_error: raise RuntimeError('lost reply')
        return {'job_id':'c'*32 if self.wrong_complete else JOB,
                'state':'succeeded' if body['result']['status']=='completed' else body['result']['status']}

class Provider:
    def __init__(self,spool): self.spool=spool
    def status(self): return {'status':'PASS'}
    def generate(self,job,text,*,segments=None,cancel=None):
        directory=self.spool/job
        directory.mkdir()
        with wave.open(str(directory/'narration.wav'),'wb') as audio:
            audio.setparams((1,2,16000,0,'NONE','not compressed'))
            audio.writeframes(b'\x01\x00'*16000)
        receipt={'provider':'voxcpm2_remote','narrator_id':'oxiegen-narrator','collector_job_id':job,
                 'status':'generated_pending_review','review_only':True,'publication_eligible':False,
                 'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'audio':inspect_wav(directory/'narration.wav'),
                 'provenance':{'script_sha256':'1'*64,'config_sha256':'2'*64,'model_revision':'test-revision','license_evidence_sha256':'3'*64},
                 'cues':[{'text':text,'start_sample':0,'end_sample':16000,'start':0,'end':1}]}
        (directory/'narration.json').write_text(json.dumps(receipt),encoding='utf-8')
        return receipt

class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp=FixtureDirectory(); self.addCleanup(self.temp.cleanup)
        self.spool=Path(self.temp.name); self.service=Service(); self.provider=Provider(self.spool)
    def run_job(self,**kw): return run_once(self.service,lambda:self.provider,**kw)
    def test_actual_pcm_hash_and_receipt_verified_completed(self):
        result=self.run_job()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['audio_sha256'],inspect_wav(self.spool/JOB/'narration.wav')['sha256'])
        self.assertEqual(result['narration_receipt_sha256'],hashlib.sha256((self.spool/JOB/'narration.json').read_bytes()).hexdigest())
        self.assertNotIn(TOKEN,json.dumps(result)); self.assertNotIn(TEXT,json.dumps(result))
        self.assertFalse(result['publication_eligible'])
    def test_idle_never_constructs_provider(self):
        self.service.idle=True; factory=Mock()
        self.assertEqual(run_once(self.service,factory),{'status':'idle'}); factory.assert_not_called()
    def test_wrong_type_denied_without_provider(self):
        self.service.type='shell'; factory=Mock()
        self.assertEqual(run_once(self.service,factory)['status'],'failed'); factory.assert_not_called()
    def test_config_block_has_no_generation(self):
        self.provider.status=Mock(return_value={'status':'BLOCKED'}); self.provider.generate=Mock()
        self.assertEqual(self.run_job()['status'],'blocked'); self.provider.generate.assert_not_called()
    def test_missing_user_credential_blocks_before_post(self):
        self.provider.status=Mock(side_effect=ValueError('BLOCKED_VOICE_CREDENTIAL_MISSING'))
        self.assertEqual(self.run_job()['status'],'blocked')
    def test_offline_or_auth_health_error_blocks_without_generation(self):
        self.provider.generate=Mock()
        for code in ('NARRATION_TRANSPORT_OUTCOME_UNKNOWN','NARRATOR_AUTH_FAILED','NARRATOR_BACKPRESSURE'):
            with self.subTest(code=code):
                self.provider.status=Mock(side_effect=VoiceError(code))
                self.assertEqual(self.run_job()['status'],'blocked')
        self.provider.generate.assert_not_called()
    def test_unknown_factory_error_sanitized_and_reconciled(self):
        result=run_once(self.service,Mock(side_effect=RuntimeError('private URL text')))
        self.assertEqual(result['status'],'reconciliation_required'); self.assertNotIn('private',json.dumps(result))
    def test_unknown_after_generation_no_retry(self):
        self.provider.generate=Mock(side_effect=VoiceError('NARRATION_TRANSPORT_OUTCOME_UNKNOWN'))
        self.assertEqual(self.run_job()['status'],'reconciliation_required'); self.provider.generate.assert_called_once()
    def test_modified_pcm_not_completed(self):
        original=self.provider.generate
        def generate(*args,**kw):
            original(*args,**kw); path=self.spool/JOB/'narration.wav'
            path.write_bytes(path.read_bytes()[:-2]+b'\x02\x00')
        self.provider.generate=generate
        self.assertEqual(self.run_job()['status'],'reconciliation_required')
    def test_wrong_receipt_job_not_completed(self):
        original=self.provider.generate
        def generate(*args,**kw):
            receipt=original(*args,**kw); receipt['collector_job_id']='c'*32
            (self.spool/JOB/'narration.json').write_text(json.dumps(receipt))
        self.provider.generate=generate
        self.assertEqual(self.run_job()['status'],'reconciliation_required')
    def test_lost_completion_no_retry(self):
        self.service.complete_error=True
        self.assertEqual(self.run_job()['error'],'COMPANION_COMPLETION_UNCERTAIN')
        self.assertEqual(sum(op=='complete' for op,_ in self.service.calls),1)
    def test_stable_service_rejection_code_survives_completion_diagnostic(self):
        original=self.service.call
        def call(op,body=None):
            if op=='complete': raise CompanionError('COMPANION_SERVICE_PRIVATE_FILE_ACL_INVALID')
            return original(op,body)
        self.service.call=call
        self.assertEqual(self.run_job()['error'],'COMPANION_SERVICE_PRIVATE_FILE_ACL_INVALID')
    def test_wrong_completion_job_reconciled(self):
        self.service.wrong_complete=True
        self.assertEqual(self.run_job()['status'],'reconciliation_required')
    def test_twelve_thousand_unicode_codepoints_with_real_pcm(self):
        self.service.text=chr(0x1f600)*12000
        self.assertEqual(self.run_job()['status'],'completed')
    def cancellation(self,observed=None,lost=False):
        self.service.heartbeat=RuntimeError('lost') if lost else {'cancel_requested':True}
        directory=self.spool/JOB; directory.mkdir()
        (directory/'narration.json').write_text(json.dumps({'host_jobs':[{'id':JOB,'state':'submission_intent'}]}))
        def generate(*args,cancel,**kw):
            self.assertTrue(cancel.wait(1)); raise VoiceError('NARRATION_CANCELLED_HOST_STATUS_UNVERIFIED')
        self.provider.generate=generate
        self.provider.cancel=Mock(return_value={'provider':'voxcpm2_remote','collector_job_id':JOB,
            'status':'HOST_STATUS_OBSERVED' if observed else 'NO_ACTIVE_HOST_JOB',
            'host_jobs':[{'id':JOB,'state':observed}] if observed else []})
        return self.run_job(heartbeat_seconds=.01)
    def test_owner_cancel_only_observed_cancelled_accepts(self):
        self.assertEqual(self.cancellation('cancelled')['status'],'cancelled'); self.provider.cancel.assert_called_once_with(JOB)
    def test_owner_cancel_still_running_not_claimed_stopped(self):
        self.assertEqual(self.cancellation('running')['status'],'reconciliation_required'); self.provider.cancel.assert_called_once_with(JOB)
    def test_no_active_response_not_claimed_cancelled(self):
        self.assertEqual(self.cancellation()['status'],'reconciliation_required')
    def test_lease_loss_overrides_even_observed_host_cancellation(self):
        self.assertEqual(self.cancellation('cancelled',lost=True)['error'],'COMPANION_LEASE_LOST')

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=FixtureDirectory(); self.addCleanup(self.temp.cleanup)
        self.spool=Path(self.temp.name); self.exe=self.spool/'kn-collector.exe'
        self.exe.write_bytes(b'fixture executable'); self.sha=hashlib.sha256(self.exe.read_bytes()).hexdigest()
        canonical=patch('youtube_ops.collector_companion.CANONICAL_EXE',self.exe)
        canonical.start(); self.addCleanup(canonical.stop)
        identity=patch('youtube_ops.collector_companion._current_identity',return_value=(1,'S-1-5-21-1-2-3-1001'))
        identity.start(); self.addCleanup(identity.stop)
    def client(self):
        with patch('youtube_ops.collector_companion.verify_spool_acl') as acl:
            client=ServiceCLI(self.sha,self.spool); acl.assert_called_once_with(self.spool); return client
    def test_session_zero_and_service_identities_denied_before_claim(self):
        for identity in ((0,'S-1-5-21-1-2-3-1001'), (1,'S-1-5-18'), (1,'S-1-5-19'), (1,'S-1-5-20')):
            with self.subTest(identity=identity), patch('youtube_ops.collector_companion._current_identity',return_value=identity), patch('youtube_ops.collector_companion.subprocess.Popen') as launch, patch('youtube_ops.collector_companion.verify_spool_acl') as acl:
                with self.assertRaises(CompanionError): ServiceCLI(self.sha,self.spool).call('claim')
                launch.assert_not_called(); acl.assert_not_called()
    def test_failed_native_identity_check_denied_before_claim(self):
        with patch('youtube_ops.collector_companion._current_identity',side_effect=CompanionError('COMPANION_IDENTITY_UNVERIFIED')), patch('youtube_ops.collector_companion.subprocess.Popen') as launch:
            with self.assertRaises(CompanionError): ServiceCLI(self.sha,self.spool).call('claim')
            launch.assert_not_called()
    def test_private_token_file_not_argv_and_transport_evidence_retained(self):
        body={'job_id':JOB,'lease_token':TOKEN}
        def start(argv,**kw):
            self.assertEqual(argv[:2],[str(self.exe),'companion-heartbeat']); self.assertNotIn(TOKEN,' '.join(argv))
            self.assertEqual(json.loads(Path(argv[2]).read_text()),body)
            kw['stdout'].write(b'{"ok":true,"result":{"cancel_requested":false}}')
            return Mock(returncode=0,poll=Mock(return_value=0))
        with patch('youtube_ops.collector_companion.subprocess.Popen',side_effect=start):
            self.assertEqual(self.client().call('heartbeat',body),{'cancel_requested':False})
        retained = list(self.spool.glob('companion-*'))
        self.assertEqual(len(retained), 1)
        self.assertEqual(json.loads((retained[0] / 'request.json').read_text()), body)
        self.assertEqual(json.loads((retained[0] / 'retention.json').read_text())['deletion_performed'], False)
        self.assertEqual(json.loads((retained[0] / 'reply.json').read_text()), {'ok': True, 'result': {'cancel_requested': False}})
    def test_executable_replaced_after_construction_denied(self):
        client=self.client(); self.exe.write_bytes(b'changed')
        with patch('youtube_ops.collector_companion.subprocess.Popen') as launch:
            with self.assertRaises(CompanionError): client.call('claim')
            launch.assert_not_called()
    def test_noncanonical_executable_denied_even_matching_digest(self):
        client=self.client()
        other=self.spool/'other'; other.mkdir()
        duplicate=other/'kn-collector.exe'; duplicate.write_bytes(self.exe.read_bytes())
        client.executable=duplicate
        with self.assertRaises(CompanionError): client.call('claim')
    def test_acl_verification_required(self):
        with patch('youtube_ops.collector_companion.verify_spool_acl',side_effect=RuntimeError()):
            with self.assertRaises(RuntimeError): ServiceCLI(self.sha,self.spool)
    def bad_reply(self,raw):
        def start(argv,**kw):
            kw['stdout'].write(raw); return Mock(returncode=0,poll=Mock(return_value=0))
        with patch('youtube_ops.collector_companion.subprocess.Popen',side_effect=start): self.client().call('claim')
    def test_oversize_reply_denied(self):
        with self.assertRaises(CompanionError): self.bad_reply(b'x'*(512*1024+1))
    def test_native_stable_service_code_propagates_safely(self):
        with self.assertRaisesRegex(CompanionError,'^COMPANION_SERVICE_PRIVATE_FILE_ACL_INVALID$'):
            self.bad_reply(b'{"ok":false,"error":"private_file_acl_invalid"}')
    def test_service_error_with_private_text_does_not_propagate(self):
        with self.assertRaisesRegex(CompanionError,'^COMPANION_SERVICE_REJECTED$'):
            self.bad_reply(b'{"ok":false,"error":"private host URL and token"}')
    def test_duplicate_reply_keys_denied(self):
        with self.assertRaises(ValueError): self.bad_reply(b'{"ok":true,"ok":true,"result":{}}')

class MainFailureTests(unittest.TestCase):
    arguments = ['--once', '--collector-sha256', 'a' * 64, '--private-spool', 'missing-spool']

    def test_known_constructor_errors_are_blocked_before_any_claim(self):
        for error, code in ((VoiceError('BLOCKED_LOCAL_VOICE_SPOOL'), 'BLOCKED_LOCAL_VOICE_SPOOL'),
                            (CompanionError('COMPANION_WINDOWS_USER_SESSION_REQUIRED'), 'COMPANION_WINDOWS_USER_SESSION_REQUIRED'),
                            (NarratorError('spool_acl_unverified'), 'SPOOL_ACL_UNVERIFIED'),
                            (NarratorError('private host URL and bearer'), 'COMPANION_OPERATION_FAILED')):
            with self.subTest(error=type(error).__name__), \
                    patch('youtube_ops.collector_companion.ServiceCLI', side_effect=error), \
                    patch.object(ServiceCLI, 'call') as claim, \
                    patch('youtube_ops.collector_companion.run_once') as run, \
                    patch('builtins.print') as output:
                self.assertEqual(main(self.arguments), 1)
                result = json.loads(output.call_args.args[0])
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['error'], code)
                self.assertFalse(result['publication_eligible'])
                run.assert_not_called()
                claim.assert_not_called()

    def test_errors_after_construction_keep_existing_uncertainty(self):
        for error, code in ((VoiceError('BLOCKED_LOCAL_VOICE_SPOOL'), 'COMPANION_TRANSPORT_UNCERTAIN'),
                            (CompanionError('COMPANION_TRANSPORT_UNCERTAIN'), 'COMPANION_TRANSPORT_UNCERTAIN'),
                            (NarratorError('spool_acl_unverified'), 'COMPANION_TRANSPORT_UNCERTAIN')):
            with self.subTest(error=type(error).__name__), \
                    patch('youtube_ops.collector_companion.ServiceCLI') as factory, \
                    patch('youtube_ops.collector_companion.run_once', side_effect=error) as run, \
                    patch('builtins.print') as output:
                self.assertEqual(main(self.arguments), 1)
                result = json.loads(output.call_args.args[0])
                self.assertEqual(result['status'], 'reconciliation_required')
                self.assertEqual(result['error'], code)
                run.assert_called_once_with(factory.return_value)


if __name__=='__main__': unittest.main()
