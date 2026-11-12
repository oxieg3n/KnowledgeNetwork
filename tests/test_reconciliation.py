import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from youtube_ops.state import State
from youtube_ops.discovery import monitor_api
from youtube_ops.network import YouTube

class API:
 def __init__(self,live='none'): self.live=live
 def list(self,resource,**params):
  return {'channels':{'items':[{'id':'UC1','contentDetails':{'relatedPlaylists':{'uploads':'UU1'}}}]},'playlistItems':{'items':[{'contentDetails':{'videoId':'abcdefghijk','videoPublishedAt':'2026-11-12T10:00:00Z'}}]},'videos':{'items':[{'id':'abcdefghijk','snippet':{'channelId':'UC1','title':'Verified title','publishedAt':'2026-11-12T10:00:00Z','liveBroadcastContent':self.live},'status':{'privacyStatus':'public'}}]}}[resource]

class ReconciliationTests(unittest.TestCase):
 def test_existing_rss_upgrades_and_preserves_editorial(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);s.enqueue('FRESH_UPLOAD','abcdefghijk',{'api_verification':'pending','editorial_notes':'keep me'})
   monitor_api(s,{'channel_id':'UC1','name':'A','categories':[]},API(),datetime(2026,11,12,15,tzinfo=timezone.utc))
   item=s.data['queues']['FRESH_UPLOAD']['abcdefghijk']
   self.assertEqual(item['api_verification'],'verified');self.assertEqual(item['editorial_notes'],'keep me')
 def test_live_completion_releases_review(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d);c={'channel_id':'UC1','name':'A','categories':[]};dt=datetime(2026,11,12,15,tzinfo=timezone.utc)
   monitor_api(s,c,API('upcoming'),dt);self.assertEqual(s.data['queues']['FRESH_UPLOAD']['abcdefghijk']['status'],'wait_for_completed_video')
   monitor_api(s,c,API(),dt);self.assertEqual(s.data['queues']['FRESH_UPLOAD']['abcdefghijk']['status'],'needs_editorial_review')
 def test_rss_root_short_id_requires_canonical(self):
  from youtube_ops.discovery import monitor_rss
  c={'channel_id':'UC123','name':'A','categories':[]}
  raw=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><yt:channelId>123</yt:channelId><link href="https://www.youtube.com/channel/UC123"/></feed>'
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(monitor_rss(State(d),c,raw,datetime.now(timezone.utc)),0)
   with self.assertRaises(ValueError):monitor_rss(State(d),c,raw.replace(b'UC123',b'UCwrong'),datetime.now(timezone.utc))
 def test_each_retry_charged_and_saved(self):
  with tempfile.TemporaryDirectory() as d:
   s=State(d)
   def fake_get(url,*,before_attempt):
    before_attempt();before_attempt();return b'{}'
   with patch('youtube_ops.network.get',fake_get):YouTube('not-real',s).list('search')
   t=State(d);self.assertEqual(next(iter(t.data['quota'].values()))['search'],2)
if __name__=='__main__':unittest.main()
