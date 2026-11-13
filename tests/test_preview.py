import hashlib,json,tempfile,unittest
from pathlib import Path
from test_licensed import fixture
from youtube_ops.licensed import validate_licensed
from youtube_ops.render_queue import validate_request,reserve_render,execute_reserved
from youtube_ops.state import State
from youtube_ops.uploader import Uploader,UploadBlocked

class PreviewTests(unittest.TestCase):
 def spec(self):
  s=fixture();s['review_purpose']='owner_private_review';a=s['licensed_assets']['source'];a.update(underlying_rights_reviewed=False,no_third_party_music=False,known_rights_conflict=False,audio_review_status='pending');return s
 def test_requires_explicit_mode_and_preserves_pending(self):
  s=self.spec();validate_licensed(s,review_only=True)
  self.assertFalse(s['licensed_assets']['source']['no_third_party_music'])
  with self.assertRaises(ValueError):validate_licensed(s)
  del s['review_purpose']
  with self.assertRaises(ValueError):validate_licensed(s,review_only=True)
 def test_known_rights_conflict_or_missing_visual_still_rejected(self):
  for k,v in [('known_rights_conflict',True),('excerpt_visual_reviewed',False),('commercial_adaptation_verified',False),('audio_review_status',None)]:
   s=self.spec();s['licensed_assets']['source'][k]=v
   with self.assertRaises(ValueError):validate_licensed(s,review_only=True)
 def test_queue_and_checkpoint_are_preview_only(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);s.enqueue('EVERGREEN_TOP10','fixture',{'status':'preview_requested'});spec=self.spec()
   r={'schema_version':1,'queue':'EVERGREEN_TOP10','item_id':'fixture','production_key':'a'*64,'rights_path':'licensed_cc_by_review_preview','purpose':'owner_private_review','script':spec,'primary_sources':spec['sources'],'distinct_value':'Fixture original value','reviewed_script_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'editorial':{k:{'status':'pass','evidence':'Fixture exact private-preview review'} for k in ('facts','sources','originality','usefulness')}}
   validate_request(r,s);cp=reserve_render(s,r,executor='dot-cloud-bounded')
   self.assertTrue(s.data['render_jobs']['a'*64]['review_only'])
   execute_reserved(s,r,output=Path(d)/'out',voice=Path('v'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],expected_request_sha256=cp['request_sha256'],readback_sha256=hashlib.sha256(s.original).hexdigest(),durable_checkpoint=lambda t:{'commit_sha':'b'*40,'readback_revision':t.data['revision'],'readback_sha256':hashlib.sha256(t.original).hexdigest()},renderer=lambda *a,**k:{'sha256':'c'*64,'publication_eligible':False,'review_only':True},local_assets={})
   self.assertEqual(s.data['queues']['EVERGREEN_TOP10']['fixture']['status'],'preview_rendered_pending_review')
   self.assertFalse(s.data['render_jobs']['a'*64]['publication_eligible'])
 def test_uploader_rejects_retained_preview_hash_or_key_despite_flags(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);s.data['render_jobs']={'a':{'production_key':'a','render_sha256':'b'*64,'review_only':True}}
   u=Uploader(None,{'destination_channel_id':'UCAaukaaw1tGA1-pP_JdkU7Q'},lambda _:None)
   for item in ({'production_key':'a','render_sha256':'c'*64},{'production_key':'other','render_sha256':'b'*64},{'review_only':True},{'review_purpose':'owner_private_review'}):
    item.update(publication_eligible=True)
    with self.assertRaisesRegex(UploadBlocked,'Owner-review preview'):u._validate(s,item)
