#!/usr/bin/env python3
# Pulls the factory's latest posts from X into tweets.json (+ their photos) for the أخبارنا page.
# Standard library only, so it runs as is on the server's python3 (a cron job every hour).
#   python3 tweets.py SITE_DIR            fetch from X
#   python3 tweets.py SITE_DIR FEED.html  use a saved copy of the feed (local tests)
#   python3 tweets.py SITE_DIR --retry    if X says "too many requests", try again 20 and 40 minutes later (cron)
# With an X API key in /etc/alhabib/x-token it reads the official API (only posts newer than the ones we have);
# without one it falls back to X's public feed, which X stopped updating in 2025.
# If X answers with nothing usable, the current tweets.json stays as it is.
import html, json, os, re, sys, time, urllib.error, urllib.request
from email.utils import parsedate_to_datetime

USER = 'alhabib_fac'
FEED = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{USER}'
KEEP = 60
KEYDIR = os.environ.get('ALHABIB_KEYDIR', '/etc/alhabib')
API = 'https://api.x.com/2'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; alhabib-site)'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r: return r.read()

def clean(t):
    text = t.get('full_text') or t.get('text') or ''
    for m in t.get('entities', {}).get('media', []): text = text.replace(m['url'], '')
    # links go (the whole card opens the post), and so do old phone numbers: the site's only number is 920066276
    text = html.unescape(re.sub(r'https?://\S+', '', text))
    lines = [re.sub(r'(?:\+?966|0)5\d(?:[\s-]?\d){7}', '', l).strip(' \t:：-') for l in text.split('\n')]
    # lines that are only hashtags / mentions add nothing on a card
    lines = [l for l in lines if l and not re.fullmatch(r'(?:[#@]\S+\s*)+', l)]
    return re.sub(r'[ \t]+', ' ', '\n'.join(lines)).strip()

def api(path, token):
    req = urllib.request.Request(API + path, headers={'Authorization': 'Bearer ' + token, **UA})
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def save_img(site, tid, url):
    img = f'img/x/{tid}.jpg'
    dest = os.path.join(site, img)
    if os.path.exists(dest): return img
    try:
        data = get(url)
        with open(dest + '.part', 'wb') as f: f.write(data)
        os.replace(dest + '.part', dest)
        return img
    except Exception: return ''

def from_api(site, token, have):
    # the account id costs one user read, so it is looked up once and kept next to the key
    idf = os.path.join(KEYDIR, 'x-user-id')
    uid = open(idf).read().strip() if os.path.exists(idf) else ''
    if not uid:
        uid = api(f'/users/by/username/{USER}', token)['data']['id']
        open(idf, 'w').write(uid)
    q = ('max_results=5&exclude=replies,retweets&tweet.fields=created_at,entities,attachments,note_tweet'
         '&expansions=attachments.media_keys&media.fields=url,preview_image_url,type')
    if have: q += '&since_id=' + max(have, key=int)
    r = api(f'/users/{uid}/tweets?{q}', token)
    media = {m['media_key']: m for m in r.get('includes', {}).get('media', [])}
    out = []
    for t in r.get('data', []):
        text = clean({'full_text': (t.get('note_tweet') or {}).get('text') or t.get('text', '')})
        ms = [media[k] for k in t.get('attachments', {}).get('media_keys', []) if k in media]
        if not text and not ms: continue
        img, video = '', False
        if ms:
            video = ms[0].get('type') in ('video', 'animated_gif')
            u = ms[0].get('url') and ms[0]['url'] + '?name=medium' or ms[0].get('preview_image_url')
            if u: img = save_img(site, t['id'], u)
        out.append({'id': t['id'], 'href': f'https://x.com/{USER}/status/{t["id"]}', 'date': t['created_at'][:10],
                    'text': text, 'img': img, 'video': video})
    return out

def fetch(tries):
    for i in range(tries):
        try: return get(FEED).decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1: sys.exit(f'X answered {e.code}; tweets.json left as it is')
            time.sleep(1200 * (i + 1))

def main(site, feed_file=None, tries=1):
    path = os.path.join(site, 'tweets.json')
    old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
    os.makedirs(os.path.join(site, 'img', 'x'), exist_ok=True)
    keyf = os.path.join(KEYDIR, 'x-token')
    if not feed_file and os.path.exists(keyf):
        try: new = from_api(site, open(keyf).read().strip(), [p['id'] for p in old])
        except urllib.error.HTTPError as e: sys.exit(f'X API answered {e.code}: {e.read()[:300]!r}; tweets.json left as it is')
        if not new: sys.exit(f'no new posts; tweets.json left as it is ({len(old)} posts)')
        return store(site, path, new, old)
    raw = open(feed_file, encoding='utf-8').read() if feed_file else fetch(tries)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', raw, re.S)
    if not m: sys.exit('X sent no timeline; tweets.json left as it is')
    entries = json.loads(m.group(1))['props']['pageProps'].get('timeline', {}).get('entries', [])
    out = []
    for e in entries:
        t = e.get('content', {}).get('tweet')
        if not t or t.get('retweeted_status') or t.get('in_reply_to_status_id_str'): continue
        if t.get('user', {}).get('screen_name', USER).lower() != USER: continue
        text = clean(t)
        media = (t.get('extended_entities') or t.get('entities', {})).get('media', [])
        if not text and not media: continue
        tid = t['id_str']
        img = save_img(site, tid, media[0]['media_url_https'] + '?name=medium') if media else ''
        out.append({'id': tid, 'href': f'https://x.com/{USER}/status/{tid}',
                    'date': parsedate_to_datetime(t['created_at']).strftime('%Y-%m-%d'),
                    'text': text, 'img': img,
                    'video': bool(media) and media[0].get('type') in ('video', 'animated_gif')})
    if not out: sys.exit('no posts found; tweets.json left as it is')
    store(site, path, out, old)

def store(site, path, new, old):
    seen, out = set(), []
    for p in sorted(new + old, key=lambda p: int(p['id']), reverse=True):
        if p['id'] not in seen: seen.add(p['id']); out.append(p)
    out = out[:KEEP]
    imgdir = os.path.join(site, 'img', 'x')
    with open(path + '.part', 'w', encoding='utf-8') as f: json.dump(out, f, ensure_ascii=False)
    os.replace(path + '.part', path)
    # photos of posts that dropped off the list
    keep = {os.path.basename(p['img']) for p in out if p['img']}
    for f in os.listdir(imgdir):
        if f.endswith('.jpg') and f not in keep: os.remove(os.path.join(imgdir, f))
    print(len(out), 'posts, newest', out[0]['date'])

if __name__ == '__main__':
    args = [a for a in sys.argv[2:] if a != '--retry']
    main(sys.argv[1], args[0] if args else None, 3 if '--retry' in sys.argv else 1)
