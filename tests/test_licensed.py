import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from youtube_ops.licensed import validate_licensed,verify_local_assets
from youtube_ops.render_queue import validate_request,reserve_render,execute_reserved
from youtube_ops.state import State

def fixture():
 a={'sha256':hashlib.sha256(b'fixture').hexdigest(),'license':'CC-BY-3.0','license_url':'https://creativecommons.org/licenses/by/3.0/',
    'source_url':'https://example.org/source','license_evidence_url':'https://example.org/license',
    'title':'Unit fixture','creator':'Fixture author','attribution':'Fixture CC BY 3.0','modifications':'Excerpt within original commentary',
    'rights_review_evidence':'Unit fixture only', **{k:True for k in ('commercial_adaptation_verified','underlying_rights_reviewed','excerpt_visual_reviewed','no_third_party_music','no_endorsement')}}
 scene={'title':'Unit fixture','narration':'Fixture source words.','caption':'Unit fixture'}
 clip={**scene,'licensed_excerpt':{'asset_id':'source','start':2,'end':5,'context_reviewed':True,'context_evidence':'Fixture context',
   'captions':[{'start':0,'end':3,'text':'Fixture source words.'}]}}
 return {'format':'short','scenes':[dict(scene),clip,dict(scene)],'sources':['https://example.org/source'],'licensed_assets':{'source':a},'original_commentary_rationale':'Unit fixture not publication','original_commentary_review':{'status':'pass','evidence':'Unit fixture only'}}

class LicensedTests(unittest.TestCase):
 def test_valid_fixture(self):validate_licensed(fixture())
 def test_fail_closed_review_fields(self):
  for k in ('sha256','license_url','creator','rights_review_evidence','commercial_adaptation_verified','underlying_rights_reviewed','excerpt_visual_reviewed','no_third_party_music','no_endorsement'):
   s=fixture();del s['licensed_assets']['source'][k]
   with self.assertRaises(ValueError,msg=k):validate_licensed(s)
 def test_unknown_license(self):
  s=fixture();s['licensed_assets']['source']['license']='standard-youtube'
  with self.assertRaises(ValueError):validate_licensed(s)
 def test_cut_bounds(self):
  for v in (-1,float('nan'),float('inf'),30):
   s=fixture();s['scenes'][1]['licensed_excerpt']['end']=v
   with self.assertRaises(ValueError):validate_licensed(s)
 def test_caption_range_and_plaintext(self):
  for k,v in [('end',4),('start',-1),('text','{injection}')]:
   s=fixture();s['scenes'][1]['licensed_excerpt']['captions'][0][k]=v
   with self.assertRaises(ValueError):validate_licensed(s)
 def test_changed_transcript(self):
  s=fixture();s['scenes'][1]['narration']='Other words'
  with self.assertRaises(ValueError):validate_licensed(s)
 def test_requires_analysis(self):
  s=fixture();s['scenes']=s['scenes'][1:]
  with self.assertRaises(ValueError):validate_licensed(s)
 def test_hash_verified_without_fetch(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source';p.write_bytes(b'fixture');verify_local_assets(fixture(),{'source':p})
   p.write_bytes(b'changed')
   with self.assertRaises(ValueError):verify_local_assets(fixture(),{'source':p})
 def test_queue_binding_and_checkpoint_retained(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);s.enqueue('FRESH_UPLOAD','lead',{'status':'ready'});spec=fixture()
   r={'schema_version':1,'queue':'FRESH_UPLOAD','item_id':'lead','production_key':'a'*64,'rights_path':'licensed_cc_by_excerpt','script':spec,
      'primary_sources':spec['sources'],'distinct_value':'Unit fixture','reviewed_script_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),
      'editorial':{k:{'status':'pass','evidence':'Unit fixture'} for k in ('facts','sources','originality','usefulness')}}
   validate_request(r,s)
   r['rights_path']='original'
   with self.assertRaises(ValueError):validate_request(r,s)
   r['rights_path']='licensed_cc_by_excerpt';cp=reserve_render(s,r,executor='dot-cloud-bounded');calls=[]
   def renderer(*args,**kwargs):calls.append(kwargs);return {'sha256':'c'*64,'publication_eligible':False}
   execute_reserved(s,r,output=Path(d)/'out',voice=Path('v'),voice_metadata={},commit_sha='b'*40,readback_revision=s.data['revision'],
     expected_request_sha256=cp['request_sha256'],readback_sha256=hashlib.sha256(s.original).hexdigest(),
     durable_checkpoint=lambda t:{'commit_sha':'b'*40,'readback_revision':t.data['revision'],'readback_sha256':hashlib.sha256(t.original).hexdigest()},
     renderer=renderer,local_assets={'source':Path('local')})
   self.assertEqual(calls,[{'local_assets':{'source':Path('local')}}]);self.assertFalse(s.data['render_jobs']['a'*64]['publication_eligible'])
