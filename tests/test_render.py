import tempfile
import unittest
from pathlib import Path
from youtube_ops.render import validate_spec, verify_voice, assess_probe, sha256

class RenderTests(unittest.TestCase):
    def test_spec_rejects_control_characters(self):
        with self.assertRaises(ValueError):
            validate_spec({'format':'short','scenes':[{'title':'a','caption':'a','narration':'a\x00'}]})
    def test_spec_rejects_empty(self):
        with self.assertRaises(ValueError): validate_spec({'format':'short','scenes':[]})
    def test_rights_and_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model';p.write_bytes(b'test')
            with self.assertRaises(ValueError): verify_voice(p,{})
            rights={'rights_reviewed':True,'license':'CC0','proof_url':'https://example.org','rights_holder':'test','model_sha256':sha256(p),'commercial_use':True,'youtube_use':True}
            verify_voice(p,rights)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_voice(p,rights)
    def test_qc_checks_streams_and_duration(self):
        data={'format':{'duration':'40'},'streams':[{'codec_type':'video','codec_name':'h264','pix_fmt':'yuv420p','width':1080,'height':1920,'avg_frame_rate':'30/1'},{'codec_type':'audio','codec_name':'aac'}]}
        self.assertTrue(assess_probe(data,(1080,1920),True)['passed'])
        data['format']['duration']='20'
        self.assertFalse(assess_probe(data,(1080,1920),True)['passed'])
    def test_qc_requires_audio(self):
        data={'format':{'duration':'40'},'streams':[]}
        self.assertFalse(assess_probe(data,(1080,1920),True)['passed'])

if __name__=='__main__': unittest.main()
