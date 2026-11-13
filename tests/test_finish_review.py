import unittest,tempfile,json,shutil
from pathlib import Path
from youtube_ops.finish_review import finish,digest,run

@unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
class FinishingTests(unittest.TestCase):
 def test_audio_timeline_and_pixels_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);source=p/'preview.mp4'
   run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=1080x1920:r=30:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)])
   manifest=p/'manifest.json';manifest.write_text(json.dumps({'sha256':digest(source),'review_only':True}))
   result=finish(source,p/'out.mp4',digest(source),segments=[{'path':str(source),'sha256':digest(source),'kind':'original'}],manifest_hash=digest(manifest),manifest_path=manifest)
   self.assertTrue(result['audio_identical']);self.assertTrue(result['outside_footer_pixels_identical']);self.assertFalse(result['publication_eligible'])
   with self.assertRaises(FileExistsError):finish(source,p/'out.mp4',digest(source),segments=[],manifest_hash='',manifest_path=manifest)
 def test_hash_fail_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);s=p/'fake.mp4';s.write_bytes(b'not media')
   with self.assertRaises(ValueError):finish(s,p/'out.mp4','0'*64,segments=[],manifest_hash='',manifest_path=p/'m')
 def test_intro_original_source_and_outside_mutation(self):
  from youtube_ops.finish_review import verify_pixels,frames,RECTANGLES
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);source=p/'preview.mp4'
   run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=1080x1920:r=30:d=3.6','-f','lavfi','-i','sine=frequency=440:duration=3.6','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)])
   segments=[]
   for i,(duration,kind) in enumerate([(1.6,'intro'),(1,'original'),(1,'source')]):
    path=p/f'seg-{i}.mp4';run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=blue:s=1080x1920:r=30:d={duration}','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(path)]);segments.append({'path':str(path),'sha256':digest(path),'kind':kind})
   manifest=p/'m.json';manifest.write_text(json.dumps({'sha256':digest(source),'review_only':True}))
   result=finish(source,p/'out.mp4',digest(source),segments=segments,manifest_hash=digest(manifest),manifest_path=manifest)
   self.assertTrue(result['outside_footer_pixels_identical'])
   bad=p/'bad.mp4';run(['ffmpeg','-v','error','-i',str(source),'-vf','drawbox=x=0:y=0:w=10:h=10:color=red:t=fill','-c:v','libx264','-crf','0','-threads','2','-c:a','copy',str(bad)])
   with self.assertRaises(ValueError):verify_pixels(source,bad,frames(source),[(0,4,RECTANGLES[0])])
