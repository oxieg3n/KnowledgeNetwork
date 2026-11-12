import hashlib
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from youtube_ops.state import State
from youtube_ops.policy import REQUIRED_CHECKS
from youtube_ops.uploader import Uploader, UploadBlocked, production_marker

CID='UCAaukaaw1tGA1-pP_JdkU7Q'
VID='abcdefghijk'

class Request:
 def __init__(self, data):self.data=data
 def execute(self, **kwargs):
  assert kwargs == {'num_retries':0}
  if isinstance(self.data,Exception):raise self.data
  return self.data

class FakeClient:
 def __init__(self, events):
  self.events=events;self.channel_id=CID;self.insert_count=0;self.marker=None
  self.processing='succeeded';self.privacy='public';self.chunk_error=None;self.omit=False
 def channels(self):return self
 def playlistItems(self):self.mode='playlist';return self
 def videos(self):self.mode='video';return self
 def list(self,**params):
  if params.get('mine'):
   self.events.append('channels.list')
   return Request({'items':[{'id':self.channel_id,'contentDetails':{'relatedPlaylists':{'uploads':'UUtest'}}}]})
  if params.get('playlistId'):
   self.events.append('playlist.list');return Request({'items':[{'contentDetails':{'videoId':VID}}]})
  self.events.append('videos.list')
  return Request({'items':[] if self.omit else [{'id':VID,'snippet':{'channelId':self.channel_id,'tags':[self.marker]},'status':{'privacyStatus':self.privacy},'processingDetails':{'processingStatus':self.processing}}]})
 def insert(self,**params):
  self.events.append('insert');self.insert_count+=1;self.body=params['body'];self.marker=self.body['snippet']['tags'][0]
  self.media=params['media_body'];return self
 def next_chunk(self,**params):
  assert params == {'num_retries':0}
  self.events.append('next_chunk')
  if self.chunk_error:raise self.chunk_error
  return None,{'id':VID}

class UploadTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.path=self.root/'reviewed.mp4';self.path.write_bytes(b'fixture media bytes')
  self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
  self.state=State(self.root/'state');self.state.data['control']={'publication_paused':False,'production_host_verified':True}
  self.events=[];self.client=FakeClient(self.events)
  self.config={'destination_channel_id':CID,'upload_enabled':True,'oauth_verified':True,'publication_paused':False}
  self.item={'production_key':'story:v1:short','destination_channel_id':CID,'render_sha256':self.digest,'reviewed_render_sha256':self.digest,'rights_path':'original','assets':[{'sha256':self.digest,'rights_holder':'Owner','license':'original','evidence':'reviewed source'}],'primary_sources':['https://example.org/source'],'checks':{k:{'status':'pass','evidence':'reviewed exact render'} for k in REQUIRED_CHECKS},'distinct_value':'Original sourced explanation','visibility':'public','made_for_kids':False,'contains_synthetic_media':True,'title':'Original explanation','description':'Sources and truthful disclosure','publication_eligible':True,'publication_format':'short','source_identity':'story:v1'}
  self.u=Uploader(self.client,self.config,self.checkpoint,media_factory=lambda f:f.read(),utcnow=lambda:datetime(2026,11,12,22,tzinfo=timezone.utc))
 def checkpoint(self,state):
  self.events.append(('checkpoint',state.data['revision'],dict(state.data['publications'].get(self.item['production_key'],{}))))
  return {'commit_sha':'a'*40,'readback_revision':state.data['revision'],'readback_sha256':hashlib.sha256(state.original).hexdigest()}
 def test_verified_upload_is_explicit_and_durable(self):
  record=self.u.upload(self.state,self.item,self.path)
  self.assertEqual(record['status'],'verified');self.assertEqual(self.client.insert_count,1)
  self.assertEqual(self.client.media,self.path.read_bytes())
  self.assertEqual(self.client.body['status'],{'privacyStatus':'public','selfDeclaredMadeForKids':False,'containsSyntheticMedia':True})
  i=self.events.index('insert');self.assertEqual(self.events[i-1][0],'checkpoint')
  j=self.events.index('videos.list');self.assertTrue(any(isinstance(x,tuple) and x[2].get('video_id')==VID for x in self.events[i:j]))
 def test_disabled_by_default(self):
  self.config.pop('upload_enabled')
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_wrong_channel_blocks(self):
  self.client.channel_id='UC'+'x'*22
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_modified_file_blocks(self):
  self.path.write_bytes(b'changed')
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertNotIn('channels.list',self.events)
 def test_pause_blocks(self):
  self.state.data['control']['publication_paused']=True
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_technical_test_cannot_upload(self):
  self.item['technical_test']=True
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
 def test_invalid_remote_proof_blocks_before_insert(self):
  self.u.checkpoint=lambda s:{'commit_sha':'a'*40,'readback_revision':s.data['revision'],'readback_sha256':'wrong'}
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
  self.assertEqual(self.state.data['publications'][self.item['production_key']]['status'],'in_flight')
 def test_ambiguous_send_cannot_repeat(self):
  self.client.chunk_error=TimeoutError('secret response must not be displayed')
  with self.assertRaisesRegex(UploadBlocked,'outcome uncertain') as raised:self.u.upload(self.state,self.item,self.path)
  self.assertNotIn('secret',str(raised.exception))
  self.assertEqual(self.state.data['publications'][self.item['production_key']]['status'],'reconciliation_required')
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,1)
 def test_processing_pending_is_not_success(self):
  self.client.processing='processing'
  record=self.u.upload(self.state,self.item,self.path)
  self.assertEqual(record['status'],'verification_pending');self.assertEqual(record['cleanup'],'not_eligible')
 def test_privacy_mismatch_not_success(self):
  self.client.privacy='private'
  record=self.u.upload(self.state,self.item,self.path)
  self.assertEqual(record['status'],'verification_pending')
 def test_missing_unique_match_never_permits_retry(self):
  self.client.chunk_error=TimeoutError()
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.client.omit=True
  with self.assertRaisesRegex(UploadBlocked,'No unique'):self.u.reconcile(self.state,self.item['production_key'])
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,1)
 def test_uncertain_response_can_be_reconciled_without_insert(self):
  self.client.chunk_error=TimeoutError()
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  record=self.u.reconcile(self.state,self.item['production_key'])
  self.assertEqual(record['status'],'verified');self.assertEqual(self.client.insert_count,1)
 def test_synthetic_assessment_required(self):
  self.item.pop('contains_synthetic_media')
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
 def test_stop_observed_during_checkpoint_blocks_insert(self):
  def checkpoint(state):
   state.data['control']['publication_paused']=True;state.save()
   return self.checkpoint(state)
  self.u.checkpoint=checkpoint
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_receipt_checkpoint_failure_preserves_known_id(self):
  def checkpoint(state):
   record=state.data['publications'][self.item['production_key']]
   if record.get('video_id'):raise RuntimeError('remote persistence unavailable')
   return self.checkpoint(state)
  self.u.checkpoint=checkpoint
  with self.assertRaises(RuntimeError):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.state.data['publications'][self.item['production_key']]['video_id'],VID)
  self.assertNotIn('videos.list',self.events)
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,1)
 def reserve(self,key,fmt='short',status='reconciliation_required',day='2026-11-12',source=None,recap_date=None):
  self.state.data['publications'][key]={'channel_id':CID,'production_key':key,'render_sha256':self.digest,
   'publication_format':fmt,'source_identity':source or key,'attempt_ny_date':day,
   'insert_quota_pt_date':day,'status':status,'recap_date':recap_date}
 def test_three_short_limit_counts_uncertain_and_inflight(self):
  for i,status in enumerate(['verified','in_flight','reconciliation_required']):self.reserve(str(i),status=status)
  with self.assertRaisesRegex(UploadBlocked,'Three Shorts'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0);self.assertNotIn('channels.list',self.events)
 def test_short_limit_resets_on_new_york_date(self):
  for i in range(3):self.reserve(str(i),day='2026-11-11')
  self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,1)
 def test_recaps_one_per_editorial_date_including_uncertain(self):
  self.reserve('prior',fmt='daily_recap',status='in_flight',recap_date='2026-11-11')
  self.item.update(publication_format='daily_recap',recap_date='2026-11-11')
  with self.assertRaisesRegex(UploadBlocked,'recap date already'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_recap_requires_real_nonfuture_date(self):
  self.item.update(publication_format='daily_recap',recap_date='2026-11-13')
  with self.assertRaisesRegex(UploadBlocked,'future'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_formats_and_source_identity_are_mandatory(self):
  for field in ('publication_format','source_identity'):
   value=self.item.pop(field)
   with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
   self.item[field]=value
  self.assertEqual(self.client.insert_count,0)
 def test_source_version_cannot_get_second_output_same_format(self):
  self.reserve('previous',fmt='blog_video',source='article:v1',status='verification_pending')
  self.item.update(publication_format='blog_video',source_identity='article:v1')
  with self.assertRaisesRegex(UploadBlocked,'Source identity'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_quota_exhaustion_blocks_before_any_insert(self):
  self.state.data['quota']['2026-11-12']={'upload':80}
  self.item['publication_format']='blog_video'
  with self.assertRaisesRegex(UploadBlocked,'quota exhausted'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0);self.assertNotIn('channels.list',self.events)
 def test_uncertain_attempt_keeps_quota_reserved(self):
  self.client.chunk_error=TimeoutError()
  with self.assertRaises(UploadBlocked):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.state.data['quota']['2026-11-12']['upload'],1)
  checkpoints=[x for x in self.events if isinstance(x,tuple)]
  self.assertEqual(checkpoints[0][2]['insert_quota_pt_date'],'2026-11-12')
 def test_quota_day_is_pacific_not_new_york(self):
  self.u.utcnow=lambda:datetime(2026,11,12,7,tzinfo=timezone.utc)
  self.u.upload(self.state,self.item,self.path)
  record=self.state.data['publications'][self.item['production_key']]
  self.assertEqual(record['attempt_ny_date'],'2026-11-12')
  self.assertEqual(record['insert_quota_pt_date'],'2026-11-11')
  self.assertEqual(self.state.data['quota']['2026-11-11']['upload'],1)
 def test_cannot_raise_conservative_quota_cap(self):
  self.config['upload_daily_limit']=100
  with self.assertRaisesRegex(UploadBlocked,'eighty'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_unclassified_legacy_intent_blocks_new_writes(self):
  self.state.data['publications']['legacy']={'channel_id':CID,'status':'in_flight'}
  with self.assertRaisesRegex(UploadBlocked,'Legacy'):self.u.upload(self.state,self.item,self.path)
  self.assertEqual(self.client.insert_count,0)
 def test_marker_binds_key_and_digest(self):
  self.assertNotEqual(production_marker('a','1'),production_marker('a','2'))
  self.assertNotEqual(production_marker('a','1'),production_marker('b','1'))

if __name__=='__main__':unittest.main()
