import tempfile
import importlib.util
import wave
import unittest
from pathlib import Path
from youtube_ops.render import validate_spec, verify_voice, assess_probe, sha256, caption_phrases, synthesize_phrases, ass_time, write_captions

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

class CaptionTests(unittest.TestCase):
    def test_phrase_timing_uses_pcm_not_word_estimate(self):
        class FakeVoice:
            def synthesize_wav(self, text, out):
                out.setnchannels(1); out.setsampwidth(2); out.setframerate(1000)
                out.writeframes(b'\x00\x00' * (300 if text == 'short' else 1700))
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / 'speech.wav'
            cues = synthesize_phrases(FakeVoice(), ['short', 'longer phrase'], wav)
            self.assertEqual(cues[0]['start'], 0)
            self.assertEqual(cues[0]['end'], .3)
            self.assertEqual(cues[1]['start'], .3)
            self.assertEqual(cues[1]['end'], 2)
            with wave.open(str(wav), 'rb') as audio:
                self.assertEqual(audio.getnframes(), 2000)
    def test_time_centisecond_rollover(self):
        self.assertEqual(ass_time(59.999), '0:01:00.00')
        self.assertEqual(ass_time(3600), '1:00:00.00')
    @unittest.skipUnless(importlib.util.find_spec('PIL') and Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').exists(), 'optional render dependencies absent')
    def test_readable_chunks_preserve_transcript_and_reject_markup(self):
        font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        text='These captions follow the actual narration. They stay readable, with safe margins and short phrases.'
        phrases=caption_phrases(text,font_path=font,width=860,px=48)
        self.assertEqual(' '.join(phrases),text)
        self.assertTrue(all(len(p.split())<=10 for p in phrases))
        with self.assertRaises(ValueError):
            caption_phrases('A {control} word',font_path=font,width=860,px=48)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'captions.ass'
            write_captions(path,[{'start':0,'end':3,'text':phrases[0]}],(1080,1920),font)
            content=path.read_text()
            self.assertIn('PlayResX: 1080',content)
            self.assertIn('pos(540,1555)',content)
            self.assertIn('Dialogue: 0,0:00:00.00,0:00:03.00',content)

if __name__=='__main__': unittest.main()
