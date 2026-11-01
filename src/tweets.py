#!/usr/bin/env python3
# Pulls the factory's latest posts from X into tweets.json (+ their photos) for the أخبارنا page.
# Standard library only, so it runs as is on the server's python3 (a cron job every hour).
#   python3 tweets.py SITE_DIR            fetch from X
#   python3 tweets.py SITE_DIR FEED.html  use a saved copy of the feed (local tests)
# If X answers with nothing usable, the current tweets.json stays as it is.
import html, json, os, re, sys, urllib.request
from email.utils import parsedate_to_datetime

USER = 'alhabib_fac'
FEED = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{USER}'
KEEP = 60
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

def main(site, feed_file=None):
    raw = open(feed_file, encoding='utf-8').read() if feed_file else get(FEED).decode('utf-8')
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', raw, re.S)
    if not m: sys.exit('X sent no timeline; tweets.json left as it is')
    entries = json.loads(m.group(1))['props']['pageProps'].get('timeline', {}).get('entries', [])
    out, imgdir = [], os.path.join(site, 'img', 'x')
    os.makedirs(imgdir, exist_ok=True)
    for e in entries:
        t = e.get('content', {}).get('tweet')
        if not t or t.get('retweeted_status') or t.get('in_reply_to_status_id_str'): continue
        if t.get('user', {}).get('screen_name', USER).lower() != USER: continue
        text = clean(t)
        media = (t.get('extended_entities') or t.get('entities', {})).get('media', [])
        if not text and not media: continue
        tid = t['id_str']
        img = ''
        if media:
            img = f'img/x/{tid}.jpg'
            dest = os.path.join(site, img)
            if not os.path.exists(dest):
                try:
                    data = get(media[0]['media_url_https'] + '?name=medium')
                    with open(dest + '.part', 'wb') as f: f.write(data)
                    os.replace(dest + '.part', dest)
                except Exception: img = ''
        out.append({'id': tid, 'href': f'https://x.com/{USER}/status/{tid}',
                    'date': parsedate_to_datetime(t['created_at']).strftime('%Y-%m-%d'),
                    'text': text, 'img': img,
                    'video': bool(media) and media[0].get('type') in ('video', 'animated_gif')})
    if not out: sys.exit('no posts found; tweets.json left as it is')
    out.sort(key=lambda p: int(p['id']), reverse=True)
    out = out[:KEEP]
    path = os.path.join(site, 'tweets.json')
    with open(path + '.part', 'w', encoding='utf-8') as f: json.dump(out, f, ensure_ascii=False)
    os.replace(path + '.part', path)
    # photos of posts that dropped off the list
    keep = {os.path.basename(p['img']) for p in out if p['img']}
    for f in os.listdir(imgdir):
        if f.endswith('.jpg') and f not in keep: os.remove(os.path.join(imgdir, f))
    print(len(out), 'posts, newest', out[0]['date'])

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
