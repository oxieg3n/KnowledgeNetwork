import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from youtube_ops.outro import TEMPLATE, ASSETS, verify_outro, append_outro, validate_config

class OutroTests(unittest.TestCase):
    def info(self, fmt):
        w,h=ASSETS[fmt]['size']
        return {'format':{'duration':'7.8'}, 'streams':[{'codec_type':'video','width':w,'height':h,'duration':'7.8'}, {'codec_type':'audio','duration':'7.8'}]}
    def test_both_approved_formats(self):
        for fmt in ASSETS:
            with patch('youtube_ops.outro.sha256',return_value=ASSETS[fmt]['sha256']), patch('youtube_ops.outro.probe',return_value=self.info(fmt)):
                self.assertTrue(verify_outro({'template':TEMPLATE},'local',fmt)['owner_approved'])
    def test_wrong_hash_rejected(self):
        with patch('youtube_ops.outro.sha256',return_value='wrong'), self.assertRaisesRegex(ValueError,'hash'):
            verify_outro({'template':TEMPLATE},'local','short')
    def test_no_custom_text_or_template(self):
        for c in [None,{}, {'template':'other'}, {'template':TEMPLATE,'text':'Other'}]:
            with self.assertRaises(ValueError):validate_config(c)
    def test_wrong_dimensions_and_duration_rejected(self):
        for field,value in [('width',1),('duration','8.0')]:
            info=self.info('short');info['streams'][0][field]=value
            with patch('youtube_ops.outro.sha256',return_value=ASSETS['short']['sha256']),patch('youtube_ops.outro.probe',return_value=info),self.assertRaises(ValueError):
                verify_outro({'template':TEMPLATE},'local','short')
    def test_append_preserves_existing_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source.mp4';source.write_bytes(b'approved')
            segments=[d/'first.mp4']
            with patch('youtube_ops.outro.verify_outro',return_value={'sha256':'hash'}),patch('youtube_ops.outro.sha256',return_value='hash'),patch('youtube_ops.outro.probe',return_value={'format':{'duration':'4.2'}}):
                result=append_outro({'template':TEMPLATE},source,'short',d,segments)
            self.assertEqual(segments[0],d/'first.mp4');self.assertEqual(result['start_seconds'],4.2)
            self.assertEqual(segments[-1].read_bytes(),b'approved')
    def test_missing_asset_fails_before_voice(self):
        from youtube_ops.render import render
        spec={'format':'short','brand_outro':{'template':TEMPLATE},'scenes':[{'title':'Test','narration':'Test','caption':'Test'}]}
        with self.assertRaisesRegex(ValueError,'poweredby_outro'):render(spec,Path('unused'),Path('unused'),{})

    def test_assembled_timeline_rejects_truncation(self):
        from youtube_ops.outro import verify_assembled_timeline
        info=self.info('short')
        self.assertTrue(verify_assembled_timeline(info,7.8))
        info['streams'][0]['duration']='3'
        self.assertFalse(verify_assembled_timeline(info,7.8))
