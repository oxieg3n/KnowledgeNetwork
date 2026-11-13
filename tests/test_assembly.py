"""Actual tiny codec fixture, not production media or a listening attestation."""
import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from youtube_ops.render import assemble_segments,probe

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg integration tools unavailable')
class AssemblyTests(unittest.TestCase):
 def test_color_metadata_transition_preserves_video_timeline(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for i,color in enumerate(('blue','red','green')):
    args=['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=90x160:r=30:d=1',
          '-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-threads','1']
    if i==1:args+=['-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv']
    subprocess.run(args+[str(root/f's{i}.mp4')],check=True,capture_output=True,timeout=30)
   concat=root/'segments.txt';concat.write_text(''.join(f"file 's{i}.mp4'\n" for i in range(3)))
   final=root/'final.mp4';assemble_segments(concat,final,branded=True)
   data=probe(final);video=next(s for s in data['streams'] if s['codec_type']=='video');audio=next(s for s in data['streams'] if s['codec_type']=='audio')
   self.assertEqual(video['avg_frame_rate'],'30/1')
   self.assertGreaterEqual(int(video['nb_frames']),89)
   self.assertLess(abs(float(video['duration'])-float(audio['duration'])),.08)
   self.assertGreater(float(video['duration']),2.95)

   for t,channel in ((.5,2),(1.5,0),(2.5,1)):
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(final),'-frames:v','1','-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'])
    self.assertEqual(max(range(3),key=lambda i:raw[i]),channel)
    self.assertGreater(raw[channel],max(raw[i] for i in range(3) if i!=channel)+40)
   frames=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(final)]))['frames']
   pts=[float(x['best_effort_timestamp_time']) for x in frames]
   self.assertTrue(all(a<b for a,b in zip(pts,pts[1:])))
   self.assertAlmostEqual(pts[-1]-pts[0],(len(pts)-1)/30,places=3)
 def test_mixed_dimensions_rejected_before_assembly(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);concat=root/'segments.txt';concat.write_text("file 'a.mp4'\nfile 'b.mp4'\n")
   def info(width):return {'streams':[{'codec_type':'video','width':width,'height':160,'pix_fmt':'yuv420p'}]}
   with patch('youtube_ops.render.probe',side_effect=[info(90),info(180)]),patch('youtube_ops.render.run') as run:
    with self.assertRaisesRegex(ValueError,'Uniform dimensions'):assemble_segments(concat,root/'out.mp4',branded=True)
    run.assert_not_called()
