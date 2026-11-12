"""Short, restartable control-plane commands; no background daemon."""
import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from .state import State, now
from .network import get, YouTube
from .discovery import seed_watchlist, monitor_rss, monitor_api, archive_channel, blog_sync
from .policy import local_date

def run(command, root, run_id):
    root=Path(root); state=State(root/'state'); result={'command':command,'run_id':run_id,'checked_at':now(),'status':'PASS','details':{},'blockers':[]}
    raw=json.loads((root/'sources/verified_channels.json').read_text()) if (root/'sources/verified_channels.json').exists() else []
    channels=raw.get('channels',[]) if isinstance(raw,dict) else raw
    api=YouTube(os.environ.get('YOUTUBE_API_KEY'),state)
    if command=='seed':
        rows,unique=seed_watchlist(root/'sources/channel_watchlist.csv')
        result['details']={'category_entries':len(rows),'distinct_names':len(unique),'verified_channels':len(channels)}
        (root/'state/watchlist_progress.json').write_text(json.dumps(unique,indent=2)+'\n')
    elif command=='monitor':
        total=0
        api_enabled=bool(os.environ.get('YOUTUBE_API_KEY'))
        batch=sorted(channels,key=lambda c:state.data['channels'].get(c['channel_id'],{}).get('last_attempt_at',''))[:2 if api_enabled else 10]
        started=time.monotonic()
        attempted=0
        for c in batch:
            if time.monotonic()-started>180: break
            attempted+=1
            try:
                if os.environ.get('YOUTUBE_API_KEY'):total+=monitor_api(state,c,api,datetime.now(timezone.utc))
                else:total+=monitor_rss(state,c,get('https://www.youtube.com/feeds/videos.xml?channel_id='+c['channel_id']),datetime.now(timezone.utc))
            except (ValueError,RuntimeError,KeyError,ET.ParseError,TimeoutError) as exc:
                result['blockers'].append(c['name']+': '+type(exc).__name__)
            finally:
                state.data['channels'].setdefault(c['channel_id'],{}).update({'last_attempt_at':now()})
                state.save()
        result['details']={'channels_registered':len(channels),'channels_attempted':attempted,'new_leads':total,'api_enabled':bool(os.environ.get('YOUTUBE_API_KEY'))}
        if attempted<len(channels):result['blockers'].append('Bounded rotating batch; not all sources checked this run')
        if not channels:result['blockers'].append('No verified sources registered')
        if not os.environ.get('YOUTUBE_API_KEY'):result['blockers'].append('YOUTUBE_API_KEY missing; official RSS discovery only, uploads playlist reconciliation pending')
    elif command=='archive':
        if not os.environ.get('YOUTUBE_API_KEY'):result['blockers'].append('YOUTUBE_API_KEY missing; ranking not run')
        else:
            pending=sorted(channels,key=lambda c:state.data['archive_progress'].get(c['channel_id'],{}).get('checked_at',''))
            result['details']['candidates']=sum(archive_channel(state,c,api) for c in pending[:3])
    elif command=='blog-sync':
        result['details']['new_versions']=blog_sync(state,get('https://poweredby.oxieg3n.com/blog/feed.xml'))
    elif command=='recap':
        day=local_date(datetime.now(timezone.utc))
        state.enqueue('DAILY_TECH_RECAP',day,{'local_date':day,'status':'needs_verified_story_lineup','story_ids':[],'rights_path':'original_required'})
        result['blockers'].append('Editorial lineup, original script and approved narration/render required; no filler generated')
    elif command=='pause':
        state.data['control']['publication_paused']=True
    elif command=='report':
        result['details']={'queues':{q:len(v) for q,v in state.data['queues'].items()},'verified_sources':len(channels),'publication_count':sum(p.get('status')=='verified' for p in state.data['publications'].values()),'pending_alerts':sum(a['status']=='pending' for a in state.data['alerts'].values()),'control':state.data['control']}
        result['blockers']=['YouTube uploader OAuth not configured','Operational email destination/route unconfirmed','Persistent production runner not verified']
    else:raise ValueError('Unknown command')
    if result['blockers']:result['status']='BLOCKED'
    state.data['runs'].append(result)
    state.data['runs']=state.data['runs'][-200:]
    state.save()
    (root/'reports').mkdir(exist_ok=True)
    (root/'reports/latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['seed','monitor','archive','blog-sync','recap','report','pause']);p.add_argument('--root',default='.');p.add_argument('--run-id',default='local')
    args=p.parse_args()
    try:run(args.command,args.root,args.run_id)
    except Exception as exc:
        # Never log raw network URLs/authentication responses.
        print(json.dumps({'status':'FAILED','command':args.command,'error_type':type(exc).__name__}),file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
