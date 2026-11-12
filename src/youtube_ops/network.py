"""Bounded HTTPS reads. No arbitrary network targets from source text."""
import json
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlencode

ALLOWED = {'www.googleapis.com', 'www.youtube.com', 'poweredby.oxieg3n.com'}
class FetchError(RuntimeError):
    pass

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def validate_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in ALLOWED or p.port not in (None,443) or p.username or p.password:
        raise ValueError('Unapproved URL')

def get(url, *, limit=4_000_000, headers=None, before_attempt=None):
    validate_url(url)
    req = urllib.request.Request(url, headers={'User-Agent':'KnowledgeNetworkMetadata/0.1', **(headers or {})})
    for attempt in range(3):
        if before_attempt: before_attempt()
        try:
            with urllib.request.build_opener(SafeRedirect()).open(req, timeout=8) as response:
                raw = response.read(limit+1)
                if len(raw)>limit: raise ValueError('Response exceeds limit')
                return raw
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:
                raise FetchError(f'HTTP {exc.code}; request details redacted') from None
        except urllib.error.URLError:
            if attempt==2: raise RuntimeError('Network unavailable; request details redacted') from None
        time.sleep(2**attempt)

class YouTube:
    def __init__(self, api_key, state, limits=None):
        self.api_key, self.state = api_key, state
        self.limits = limits or {'general':8000, 'search':80, 'upload':80}
    def list(self, resource, **params):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
        bucket = 'search' if resource=='search' else 'general'
        counter = self.state.data['quota'].setdefault(day, {'general':0,'search':0,'upload':0})
        if not self.api_key: raise RuntimeError('YOUTUBE_API_KEY missing')
        def charge():
            if counter[bucket]+1>self.limits[bucket]: raise RuntimeError('Local API budget exhausted')
            counter[bucket]+=1
            self.state.save()
        return json.loads(get('https://www.googleapis.com/youtube/v3/'+resource+'?'+urlencode({**params,'key':self.api_key}), before_attempt=charge))
