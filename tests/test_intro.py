import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from youtube_ops.intro import verify_intro, TEMPLATE, LOGO_SHA256

class IntroValidationTests(unittest.TestCase):
    def test_exact_logo_and_title(self):
        with patch('youtube_ops.intro.sha256', return_value=LOGO_SHA256):
            self.assertEqual(verify_intro({'template':TEMPLATE,'title':'  A useful title  '},Path('badge')),'A useful title')
    def test_rejects_substitute_logo(self):
        with patch('youtube_ops.intro.sha256', return_value='0'*64):
            with self.assertRaises(ValueError):
                verify_intro({'template':TEMPLATE,'title':'Example'},Path('badge'))
    def test_rejects_unsupported_template(self):
        with self.assertRaises(ValueError):
            verify_intro({'template':'other','title':'Example'},Path('badge'))
    def test_rejects_missing_long_and_control_titles(self):
        for title in ['', ' ', 'x'*101, 'title\nsecond', 'a\x00b', 123]:
            with self.subTest(title=title), self.assertRaises(ValueError):
                verify_intro({'template':TEMPLATE,'title':title},Path('badge'))
    def test_renderer_requires_bound_local_logo_before_voice(self):
        from youtube_ops.render import render
        spec={'format':'short','scenes':[{'title':'Test','narration':'Test narration.','caption':'Test'}],
              'brand_intro':{'template':TEMPLATE,'title':'Test'}}
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError,'poweredby_logo'):
            render(spec,Path(tmp)/'output',Path('no-model'),{})
    def test_licensed_validation_keeps_exact_source_scope_separate(self):
        from youtube_ops.render import render
        spec={'format':'short','scenes':[{'title':'Test','narration':'Test narration.','caption':'Test'}],
              'licensed_assets':{'source':{}},
              'brand_intro':{'template':TEMPLATE,'title':'Test'}}
        with patch('youtube_ops.licensed.verify_local_assets') as verify,              patch('youtube_ops.intro.verify_intro'),              patch('youtube_ops.render.verify_voice',side_effect=ValueError('stop before voice')):
            with self.assertRaisesRegex(ValueError,'stop before voice'):
                render(spec,Path('unused'),Path('no-model'),{},
                       local_assets={'source':'local-source','poweredby_logo':'local-badge','unexpected':'extra'})
        verify.assert_called_once_with(spec,{'source':'local-source','unexpected':'extra'})
    def test_offset_retains_source_text_and_scene(self):
        from youtube_ops.intro import offset_captions
        cues=[{'start':0,'end':1.25,'text':'Exact licensed words','scene':2}]
        self.assertEqual(offset_captions(cues,1.6),
                         [{'start':1.6,'end':2.85,'text':'Exact licensed words','scene':2}])
        self.assertEqual(cues[0]['start'],0)
        for duration in [0,10,float('nan')]:
            with self.assertRaises(ValueError): offset_captions(cues,duration)
