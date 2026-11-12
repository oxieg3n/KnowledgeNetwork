import tempfile
import unittest
from youtube_ops.state import State
from youtube_ops.recovery import (
    upload_intent, upload_ambiguous, reconcile_upload, confirm_not_created,
    retry_upload_intent, validate_durable_checkpoint, cleanup_intent,
    reconcile_cleanup, email_intent, reconcile_email,
)

CHANNEL = 'UC' + 'a'*22
DIGEST = 'b'*64
COMMIT = 'c'*40
VIDEO = 'd'*11

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = State(self.tmp.name)

    def intent(self, artifact=123):
        return upload_intent(self.state, 'story:version:short', CHANNEL, DIGEST,
                             'public', artifact_id=artifact)

    def verified(self):
        self.intent()
        return reconcile_upload(self.state, 'story:version:short', channel_id=CHANNEL,
            render_sha256=DIGEST, video_id=VIDEO, processing_status='succeeded',
            actual_visibility='public', evidence='Authenticated videos.list receipt',
            exact_match_verified=True)

    def test_intent_is_saved_before_external_work(self):
        result = self.intent()
        restored = State(self.tmp.name)
        self.assertEqual('in_flight', restored.data['publications']['story:version:short']['status'])
        self.assertEqual(1, result['revision'])
        validate_durable_checkpoint(restored, result['revision'], COMMIT, result['revision'])

    def test_durable_checkpoint_rejects_stale_or_unconfirmed(self):
        result = self.intent()
        for args in [(result['revision'], '', result['revision']), (1, COMMIT, 2), (0, COMMIT, 0)]:
            with self.assertRaises(ValueError): validate_durable_checkpoint(self.state, *args)

    def test_crash_before_or_during_send_blocks_duplicate(self):
        self.intent()
        self.state = State(self.tmp.name)
        with self.assertRaises(RuntimeError): self.intent()
        upload_ambiguous(self.state, 'story:version:short')
        with self.assertRaises(RuntimeError): retry_upload_intent(self.state, 'story:version:short')

    def test_no_creation_must_be_definitive(self):
        self.intent()
        with self.assertRaises(ValueError):
            confirm_not_created(self.state, 'story:version:short', evidence='Empty search', definitive_no_creation=False)
        confirm_not_created(self.state, 'story:version:short', evidence='API rejected before creation', definitive_no_creation=True)
        result=retry_upload_intent(self.state, 'story:version:short')
        self.assertEqual(2, result['record']['attempt'])
        with self.assertRaises(RuntimeError): retry_upload_intent(self.state, 'story:version:short')

    def test_exact_identity_required(self):
        self.intent()
        for channel,digest in [('UC'+'z'*22,DIGEST),(CHANNEL,'e'*64)]:
            with self.assertRaises(ValueError):
                reconcile_upload(self.state, 'story:version:short', channel_id=channel, render_sha256=digest,
                    video_id=VIDEO, processing_status='succeeded', actual_visibility='public', evidence='read', exact_match_verified=True)

    def test_processing_or_visibility_pending_prevents_cleanup(self):
        self.intent()
        for processing, visibility in [('processing','public'), ('succeeded','private')]:
            reconcile_upload(self.state, 'story:version:short', channel_id=CHANNEL, render_sha256=DIGEST,
                video_id=VIDEO, processing_status=processing, actual_visibility=visibility, evidence='read', exact_match_verified=True)
            with self.assertRaises(RuntimeError): self.cleanup()

    def cleanup(self, artifact=123, copy=True, committed=True):
        return cleanup_intent(self.state, 'story:version:short', artifact_id=artifact,
            publication_commit=COMMIT, publication_readback_verified=committed,
            equivalent_copy={'sha256':DIGEST,'verified':copy,'reference':'owner-controlled-recovery-copy'})

    def test_verified_receipt_cannot_be_downgraded(self):
        self.verified()
        with self.assertRaises(RuntimeError):
            reconcile_upload(self.state, 'story:version:short', channel_id=CHANNEL,
                render_sha256=DIGEST, video_id=VIDEO, processing_status='processing',
                actual_visibility='public', evidence='Changed result', exact_match_verified=True)
        self.assertEqual('verified', self.state.data['publications']['story:version:short']['status'])

    def test_cleanup_requires_exact_id_and_recoverable_copy(self):
        self.verified()
        with self.assertRaises(ValueError): self.cleanup(artifact=124)
        with self.assertRaises(RuntimeError): self.cleanup(copy=False)
        with self.assertRaises(RuntimeError): self.cleanup(committed=False)
        self.cleanup()

    def test_crash_after_verified_upload_does_not_reupload(self):
        self.verified()
        self.state = State(self.tmp.name)
        with self.assertRaises(RuntimeError): self.intent()
        self.cleanup()
        self.state = State(self.tmp.name)
        with self.assertRaises(RuntimeError): self.cleanup()
        reconcile_cleanup(self.state, 'story:version:short', artifact_id=123,http_status=404,exact_artifact_absent_verified=True)
        self.assertEqual('deleted',self.state.data['publications']['story:version:short']['cleanup'])

    def test_failed_cleanup_retries_cleanup_only(self):
        self.verified();self.cleanup()
        reconcile_cleanup(self.state, 'story:version:short', artifact_id=123,http_status=500)
        self.cleanup()
        reconcile_cleanup(self.state, 'story:version:short', artifact_id=123,http_status=204)
        with self.assertRaises(RuntimeError): self.intent()

    def test_unknown_artifact_404_not_claimed_deleted(self):
        self.verified();self.cleanup()
        reconcile_cleanup(self.state, 'story:version:short', artifact_id=123,http_status=404)
        self.assertEqual('failed',self.state.data['publications']['story:version:short']['cleanup'])

    def test_email_acceptance_not_delivery_and_no_duplicate(self):
        self.state.alert('digest:1', {'kind':'digest'})
        email_intent(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64)
        self.state=State(self.tmp.name)
        with self.assertRaises(RuntimeError): email_intent(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64)
        reconcile_email(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64,provider_message_id='provider-1',outcome='accepted',evidence='Provider send response')
        self.assertEqual('accepted',self.state.data['alerts']['digest:1']['status'])
        reconcile_email(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64,provider_message_id='provider-1',outcome='delivered',evidence='Recipient mailbox readback')
        self.assertEqual('delivered',self.state.data['alerts']['digest:1']['status'])

    def test_unknown_email_remains_blocked(self):
        self.state.alert('digest:1', {'kind':'digest'})
        email_intent(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64)
        reconcile_email(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64,provider_message_id='',outcome='unknown',evidence='Timeout')
        with self.assertRaises(RuntimeError): email_intent(self.state,'digest:1',destination_sha256=DIGEST,message_sha256='e'*64)
        with self.assertRaises(ValueError): reconcile_email(self.state,'digest:1',destination_sha256='f'*64,message_sha256='e'*64,provider_message_id='x',outcome='accepted',evidence='wrong recipient')

if __name__ == '__main__': unittest.main()
