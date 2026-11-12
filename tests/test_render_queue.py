import hashlib,json,tempfile,unittest
from pathlib import Path
from youtube_ops.state import State
from youtube_ops.render_queue import reserve_render,execute_reserved,record_handoff

class RenderQueueTests(unittest.TestCase):
 def request(self,s):
  s.enqueue('FRESH_UPLOAD','lead',{'status':'ready'})
  script={'format':'short','sources':['https://example.com/primary'],'scenes':[{'title':'Example','narration':'This is a fixture, never real reporting.','caption':'Fixture only.'}]}
  return {'schema_version':1,'queue':'FRESH_UPLOAD','item_id':'lead','production_key':'a'*64,'rights_path':'original','primary_sources':script['sources'],'distinct_value':'test fixture','script':script,'reviewed_script_sha256':hashlib.sha256(json.dumps(script,sort_keys=True).encode()).hexdigest(),'editorial':{k:{'status':'pass','evidence':'unit fixture'} for k in ('facts','sources','originality','usefulness')}}
 def test_no_source_approval_no_render(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);r['editorial']={}
   with self.assertRaises(ValueError):reserve_render(s,r,executor='dot-cloud-bounded')
 def test_one_reservation_survives_restart(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);reserve_render(s,r,executor='dot-cloud-bounded')
   with self.assertRaises(RuntimeError):reserve_render(State(d),r,executor='dot-cloud-bounded')
 def test_changed_script_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);reserve_render(s,r,executor='dot-cloud-bounded');r['script']['scenes'][0]['title']='Changed'
   with self.assertRaises(ValueError):execute_reserved(s,r,output=Path(d)/'out',voice=Path('voice'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],expected_request_sha256='a'*64,readback_sha256='x',durable_checkpoint=lambda s:{})
 def test_checkpoint_before_render_and_review_still_pending(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);checkpoint=reserve_render(s,r,executor='dot-cloud-bounded');calls=[]
   def renderer(*args):calls.append(1);return {'sha256':'c'*64,'publication_eligible':False}
   kwargs=dict(output=Path(d)/'out',voice=Path('voice'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],expected_request_sha256=checkpoint['request_sha256'],readback_sha256=hashlib.sha256(s.original).hexdigest(),durable_checkpoint=lambda t:{'commit_sha':'b'*40,'readback_revision':t.data['revision'],'readback_sha256':hashlib.sha256(t.original).hexdigest()},renderer=renderer)
   bad={**kwargs,'readback_revision':0}
   with self.assertRaises(ValueError):execute_reserved(s,r,**bad)
   self.assertFalse(calls);execute_reserved(s,r,**kwargs);self.assertEqual(calls,[1])
   self.assertEqual(s.data['render_jobs']['a'*64]['media_handoff'],'pending')
 def test_failed_render_cannot_restart_without_reconciliation(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);cp=reserve_render(s,r,executor='dot-cloud-bounded')
   def fail(*args):raise RuntimeError('encoder interrupted')
   def checkpoint(t):return {'commit_sha':'b'*40,'readback_revision':t.data['revision'],'readback_sha256':hashlib.sha256(t.original).hexdigest()}
   args=dict(output=Path(d)/'out',voice=Path('v'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],expected_request_sha256=cp['request_sha256'],readback_sha256=hashlib.sha256(s.original).hexdigest(),durable_checkpoint=checkpoint,renderer=fail)
   with self.assertRaises(RuntimeError):execute_reserved(s,r,**args)
   self.assertEqual(State(d).data['render_jobs']['a'*64]['status'],'execution_started')
   with self.assertRaises(RuntimeError):execute_reserved(s,r,**args)
 def test_wrong_remote_bytes_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);cp=reserve_render(s,r,executor='dot-cloud-bounded')
   with self.assertRaises(ValueError):execute_reserved(s,r,output=Path(d)/'out',voice=Path('v'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],expected_request_sha256=cp['request_sha256'],readback_sha256='0'*64,durable_checkpoint=lambda t:{})
 def test_technical_test_forbidden(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);r=self.request(s);r['script']['technical_test']=True
   with self.assertRaises(ValueError):reserve_render(s,r,executor='dot-cloud-bounded')
if __name__=='__main__':unittest.main()
