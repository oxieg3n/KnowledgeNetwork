"""Discovery records are leads, never evidence of publication readiness."""
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from .network import get
from .state import key, now

NS = {'a':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}

def seed_watchlist(path):
    channels = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        name = row['channel_name']
        item = channels.setdefault(name, {'name':name,'categories':[], 'verification':'pending'})
        if row['category'] not in item['categories']: item['categories'].append(row['category'])
    return rows, channels

def monitor_rss(state, channel, raw, instant):
    root = ET.fromstring(raw)
    root_id=root.findtext('yt:channelId', namespaces=NS)
    canonical='https://www.youtube.com/channel/'+channel['channel_id']
    canonical_match=any(x.get('href')==canonical for x in root.findall('a:link',NS))
    # Official feeds sometimes omit UC on the root ID; entries retain it.
    if root_id != channel['channel_id'] and not (root_id==channel['channel_id'][2:] and canonical_match):
        raise ValueError('RSS channel identity mismatch')
    count = 0
    for entry in root.findall('a:entry', NS):
        vid = entry.findtext('yt:videoId', namespaces=NS)
        posted = entry.findtext('a:published', namespaces=NS)
        if not vid or not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid): continue
        if entry.findtext('yt:channelId', namespaces=NS) != channel['channel_id']: continue
        date = datetime.fromisoformat(posted.replace('Z','+00:00'))
        if not instant-timedelta(days=7)<=date<=instant: continue
        item = {'video_id':vid,'channel_id':channel['channel_id'],'channel_name':channel['name'],
                'url':'https://www.youtube.com/watch?v='+vid, 'published_at':posted,
                'title':entry.findtext('a:title',default='',namespaces=NS), 'categories':channel['categories'],
                'rights_path':'original_required','metadata_source':'official_atom_feed',
                'api_verification':'pending','primary_sources':[], 'story_cluster_id':None}
        if state.enqueue('FRESH_UPLOAD',vid,item):
            count += 1
            state.alert('video:'+vid, {'kind':'new_video','video_id':vid,'url':item['url'],'title':item['title']})
    state.data['channels'][channel['channel_id']] = {**channel, 'last_monitored_at':now(),
        'monitor_method':'official_atom_feed', 'coverage':'feed_window_only; API reconciliation pending'}
    return count

def monitor_api(state, channel, api, instant):
    c=api.list('channels', part='contentDetails', id=channel['channel_id']).get('items',[])
    if not c or c[0]['id'] != channel['channel_id']: raise ValueError('Channel unavailable')
    playlist=c[0]['contentDetails']['relatedPlaylists']['uploads']
    ids=[]; token=None
    for _ in range(4):
        p={'part':'snippet,contentDetails','playlistId':playlist,'maxResults':50}
        if token:p['pageToken']=token
        data=api.list('playlistItems',**p)
        for x in data.get('items',[]):
            at=x['contentDetails'].get('videoPublishedAt')
            if at and datetime.fromisoformat(at.replace('Z','+00:00'))>=instant-timedelta(days=7): ids.append(x['contentDetails']['videoId'])
        token=data.get('nextPageToken')
        if not token or not data.get('items') or (data['items'][-1]['contentDetails'].get('videoPublishedAt','') < (instant-timedelta(days=7)).isoformat()):break
    count=0
    for offset in range(0,len(ids),50):
        for v in api.list('videos',part='snippet,status,contentDetails',id=','.join(ids[offset:offset+50])).get('items',[]):
            s=v['snippet']; vid=v['id']
            if s['channelId'] != channel['channel_id'] or v['status'].get('privacyStatus')!='public':continue
            item={'video_id':vid,'channel_id':channel['channel_id'],'channel_name':channel['name'],'url':'https://www.youtube.com/watch?v='+vid,'title':s['title'],'published_at':s['publishedAt'],'categories':channel['categories'],'metadata_source':'youtube_data_api','api_verification':'verified','live_state':s.get('liveBroadcastContent'),'rights_path':'original_required','primary_sources':[]}
            if s.get('liveBroadcastContent') in ('live','upcoming'): item['status']='wait_for_completed_video'
            existing=state.data['queues']['FRESH_UPLOAD'].get(vid)
            if existing:
                # Refresh verified metadata without replacing editorial/recovery state.
                for field in ('title','published_at','api_verification','metadata_source','live_state'):
                    existing[field]=item.get(field)
                if existing.get('status')=='wait_for_completed_video' and s.get('liveBroadcastContent')=='none':
                    existing['status']='needs_editorial_review'
                elif s.get('liveBroadcastContent') in ('live','upcoming') and existing.get('status')=='needs_editorial_review':
                    existing['status']='wait_for_completed_video'
            elif state.enqueue('FRESH_UPLOAD',vid,item):
                count+=1;state.alert('video:'+vid,{'kind':'new_video','video_id':vid,'url':item['url'],'title':item['title']})
    state.data['channels'][channel['channel_id']]={**channel,'uploads_playlist_id':playlist,'last_monitored_at':now(),'monitor_method':'youtube_data_api','pagination_remaining':bool(token)}
    return count

def archive_channel(state, channel, api):
    data=api.list('search',part='snippet',channelId=channel['channel_id'],order='viewCount',type='video',maxResults=10)
    ids=[x['id']['videoId'] for x in data.get('items',[]) if x['id'].get('videoId')]
    videos=api.list('videos',part='snippet,statistics,status',id=','.join(ids)).get('items',[]) if ids else []
    valid=[v for v in videos if v['snippet']['channelId']==channel['channel_id'] and v['status'].get('privacyStatus')=='public']
    valid.sort(key=lambda v:int(v.get('statistics',{}).get('viewCount',0)),reverse=True)
    for rank,v in enumerate(valid,1):
        state.enqueue('EVERGREEN_TOP10',v['id'],{'video_id':v['id'],'channel_id':channel['channel_id'],'title':v['snippet']['title'],'url':'https://www.youtube.com/watch?v='+v['id'],'view_count':int(v.get('statistics',{}).get('viewCount',0)),'collected_at':now(),'rank':rank,'ranking':'best_available','categories':channel['categories'],'rights_path':'original_required'})
    state.data['archive_progress'][channel['channel_id']]={'checked_at':now(),'count':len(valid),'ranking':'best_available'}
    return len(valid)

def blog_sync(state, feed_raw, fetch=get):
    root=ET.fromstring(feed_raw)
    if root.tag!='rss': raise ValueError('Expected RSS, not an access/error page')
    count=0
    for item in root.findall('./channel/item'):
        url=item.findtext('link','');p=urlparse(url)
        if p.scheme!='https' or p.netloc!='poweredby.oxieg3n.com' or not p.path.startswith('/blog/') or p.query:continue
        raw=fetch(url);html=raw.decode('utf-8')
        canonical=re.search(r'<link\b(?=[^>]*\brel=["\']canonical["\'])(?=[^>]*\bhref=["\']([^"\']+)["\'])[^>]*>',html,re.I)
        if not canonical or canonical.group(1)!=url or '<article' not in html: continue
        digest_match=re.search(r'<meta\b[^>]*(?:article-sha256|article-digest)[^>]*content=["\']([a-f0-9]{64})',html)
        article=re.search(r'<article\b.*?</article>',html,re.S)
        digest=digest_match.group(1) if digest_match else hashlib.sha256(article.group(0).encode()).hexdigest()
        item_id=key(url,digest)
        if state.enqueue('BLOG_VIDEO',item_id,{'canonical_url':url,'source_version':digest,'title':item.findtext('title',''),'original_published_at':item.findtext('pubDate',''),'rights_path':'original_required','live_verified_at':now(),'primary_sources':[]}):count+=1
        previous=state.data['blog_versions'].get(url)
        if previous and previous!=digest:state.data['queues']['BLOG_VIDEO'][item_id]['status']='source_update_review'
        state.data['blog_versions'][url]=digest
    return count
