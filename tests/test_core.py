import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from youtube_ops.state import State
from youtube_ops.policy import local_date, publication_blockers, next_ready
from youtube_ops.discovery import monitor_rss, seed_watchlist, blog_sync
from youtube_ops.network import validate_url, YouTube

class CoreTests(unittest.TestCase):
 def test_four_queues_persist(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);self.assertEqual(len(s.data['queues']),4);self.assertTrue(s.enqueue('FRESH_UPLOAD','v',{}));s.save()
   t=State(d);self.assertFalse(t.enqueue('FRESH_UPLOAD','v',{}));self.assertEqual(t.data['revision'],1)
 def test_conflicting_writer(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=State(d),State(d);a.save()
   with self.assertRaises(RuntimeError):b.save()
 def test_alert_dedup(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);self.assertTrue(s.alert('a',{}));self.assertFalse(s.alert('a',{}))
 def test_timezone_dst(self):
  self.assertEqual(local_date(datetime(2026,11,2,3,tzinfo=timezone.utc)),'2026-11-01')
  self.assertEqual(local_date(datetime(2026,7,2,3,tzinfo=timezone.utc)),'2026-07-01')
  with self.assertRaises(ValueError):local_date(datetime(2026,1,1))
 def test_rights_fail_closed(self):
  blockers=publication_blockers({},{});self.assertIn('publication_paused',blockers);self.assertIn('rights_not_cleared',blockers)
 def test_unapproved_hosts(self):
  for url in ['http://www.youtube.com/','https://localhost/','https://www.youtube.com.evil.test/','https://a:b@www.youtube.com/','https://www.youtube.com:444/']:
   with self.assertRaises(ValueError):validate_url(url)
 def test_feed_identity(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d)
   with self.assertRaises(ValueError):monitor_rss(s,{'channel_id':'real'},b'<feed/>',datetime.now(timezone.utc))
 def test_feed_dedup(self):
  raw=b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><yt:channelId>UC1</yt:channelId><entry><yt:channelId>UC1</yt:channelId><yt:videoId>abcdefghijk</yt:videoId><published>2026-11-12T10:00:00Z</published><title>Lead, not verified fact</title></entry></feed>'''
  with tempfile.TemporaryDirectory() as d:
   s=State(d);c={'channel_id':'UC1','name':'A','categories':['AI']};dt=datetime(2026,11,12,15,tzinfo=timezone.utc)
   self.assertEqual(monitor_rss(s,c,raw,dt),1);self.assertEqual(monitor_rss(s,c,raw,dt),0)
   self.assertEqual(s.data['queues']['FRESH_UPLOAD']['abcdefghijk']['api_verification'],'pending')
 def test_blog_error_page_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):blog_sync(State(d),b'<html>Site Unavailable</html>')
 def test_blog_version_dedup(self):
  url='https://poweredby.oxieg3n.com/blog/test/'
  feed=f'<rss><channel><item><title>T</title><link>{url}</link></item></channel></rss>'.encode()
  page=f'<html><link rel="canonical" href="{url}"><article>Verified public article</article></html>'.encode()
  with tempfile.TemporaryDirectory() as d:
   s=State(d);self.assertEqual(blog_sync(s,feed,lambda u:page),1);self.assertEqual(blog_sync(s,feed,lambda u:page),0)
 def test_priority_does_not_interrupt_render(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);s.enqueue('EVERGREEN_TOP10','a',{'status':'rendering'});s.enqueue('FRESH_UPLOAD','b',{'status':'ready','verified_breaking':True})
   self.assertIsNone(next_ready(s.data,datetime.now(timezone.utc)))
 def test_quota_local_guard(self):
  with tempfile.TemporaryDirectory() as d:
   api=YouTube('fake',State(d),{'general':0,'search':0,'upload':0})
   with self.assertRaisesRegex(RuntimeError,'budget'):api.list('search')
 def test_watchlist(self):
  rows,channels=seed_watchlist('sources/channel_watchlist.csv');self.assertEqual(len(rows),150);self.assertEqual(len(channels),121)
if __name__=='__main__':unittest.main()
