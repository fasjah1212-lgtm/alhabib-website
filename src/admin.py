#!/usr/bin/env python3
# Control panel for the Alhabib site: alhabibfactory.com/admin (nginx passes /admin to this program on 127.0.0.1).
# Standard library + Pillow (python3-pil) for photos. Python 3.8+.
#   python3 admin.py              run the panel (systemd service alhabib-admin)
#   python3 admin.py --password   set the panel's user name and password (asks on the screen; nothing is shown)
#   python3 admin.py --apply      put the saved changes onto the site files (update.sh runs this after every update)
#   python3 admin.py --stats      fold the server's visit logs into the visitor counts (cron, once a day)
# How it works: update.sh keeps an untouched copy of each page in DATA/pristine. Every change made in the panel is
# stored in DATA/content.json (and photos in DATA/files/<version>/), and "apply" writes the pages from the pristine
# copies plus those changes, so a site update never loses them and any older version can be put back.
import base64, getpass, glob, gzip, hashlib, hmac, html, http.server, io, json, os, re, secrets, shutil, socketserver
import sys, threading, time, urllib.parse
from datetime import datetime, timedelta, date

SITE = os.environ.get('ALHABIB_SITE', '/var/www/alhabib-new')
DATA = os.environ.get('ALHABIB_DATA', '/var/lib/alhabib')
LOGS = os.environ.get('ALHABIB_LOGS', '/var/log/nginx/access.log*')
PORT = int(os.environ.get('ALHABIB_ADMIN_PORT', '8095'))
DOMAIN = 'alhabibfactory.com'
PAGES = [('index.html', 'الرئيسية'), ('products.html', 'منتجاتنا'), ('works.html', 'أعمالنا'), ('services.html', 'خدماتنا'),
         ('news.html', 'أخبارنا'), ('branches.html', 'مواقع الفروع'), ('franchise.html', 'الامتياز التجاري'), ('contact.html', 'اتصل بنا')]
LOCK = threading.Lock()

def p(*a): return os.path.join(DATA, *a)
def load(path, default):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return default
def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.part', 'w', encoding='utf-8') as f: json.dump(obj, f, ensure_ascii=False)
    os.replace(path + '.part', path)
def write_text(path, s):
    with open(path + '.part', 'w', encoding='utf-8') as f: f.write(s)
    os.replace(path + '.part', path)

EMPTY = {'texts': {}, 'images': {}, 'works': {'added': [], 'hidden': [], 'edits': {}}, 'clients': {'added': [], 'hidden': []}, 'promo': None, 'ops': []}
def content():
    c = load(p('content.json'), {})
    for k, v in EMPTY.items(): c.setdefault(k, json.loads(json.dumps(v)))
    for k, v in EMPTY['works'].items(): c['works'].setdefault(k, json.loads(json.dumps(v)))
    return c

# ---------------- pages: find, read and replace the editable parts ----------------
def pristine(name):
    with open(p('pristine', name), encoding='utf-8') as f: return f.read()
def site_data():
    return load(os.path.join(SITE, 'site-data.json'), {'works': [], 'filters': [], 'clients': [], 'promo': None})

def find_elements(s, key):
    """(inner_start, inner_end) of every element carrying data-e="key"."""
    out = []
    for m in re.finditer(r'<([a-zA-Z0-9]+)\b[^>]*\sdata-e="%s"[^>]*>' % re.escape(key), s):
        tag, depth, i = m.group(1).lower(), 1, m.end()
        for t in re.finditer(r'<(/?)%s\b[^>]*>' % tag, s[i:], re.I):
            depth += -1 if t.group(1) else 1
            if depth == 0: out.append((i, i + t.start())); break
    return out

def editable_texts():
    """{key: {'html': original, 'tag': tag, 'pages': [...]}} in page order."""
    out = {}
    for name, _ in PAGES:
        try: s = pristine(name)
        except OSError: continue
        for m in re.finditer(r'<([a-zA-Z0-9]+)\b[^>]*\sdata-e="([0-9a-f]{10})"[^>]*>', s):
            key = m.group(2)
            if key not in out:
                spans = find_elements(s, key)
                if not spans: continue
                out[key] = {'html': s[spans[0][0]:spans[0][1]].strip(), 'tag': m.group(1).lower(), 'pages': []}
            if name not in out[key]['pages']: out[key]['pages'].append(name)
    return out

INLINE = {'br', 'em', 'b', 'strong', 'i', 'u', 'span', 'bdi', 'small'}
from html.parser import HTMLParser
class Sanitize(HTMLParser):
    """Keeps text and the few inline tags the site's texts use (class attribute only); everything else goes."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.open = []
    def handle_starttag(self, tag, attrs):
        if tag in ('div', 'p') and self.out: self.out.append('<br>'); return
        if tag == 'br': self.out.append('<br>'); return
        if tag in INLINE:
            cls = ' '.join(v for k, v in attrs if k == 'class' and v and re.fullmatch(r'[a-z0-9 _-]+', v))
            self.out.append(f'<{tag} class="{cls}">' if cls else f'<{tag}>'); self.open.append(tag)
    def handle_endtag(self, tag):
        if tag in INLINE and tag != 'br' and tag in self.open:
            while self.open:
                t = self.open.pop(); self.out.append(f'</{t}>')
                if t == tag: break
    def handle_data(self, d): self.out.append(html.escape(d.replace('\xa0', ' '), quote=False))
    def result(self):
        while self.open: self.out.append(f'</{self.open.pop()}>')
        s = ''.join(self.out)
        s = re.sub(r'(<br>\s*)+$', '', re.sub(r'^(\s*<br>)+', '', s))
        return s.strip()
def sanitize(s):
    h = Sanitize(); h.feed(s or ''); h.close(); return h.result()

def block(s, name):
    a, b = f'<!--{name}-->', f'<!--/{name}-->'
    i, j = s.find(a), s.find(b)
    return (i + len(a), j) if i >= 0 and j > i else None
def put_block(s, name, new):
    r = block(s, name)
    return s[:r[0]] + new + s[r[1]:] if r else s

E = lambda t: html.escape(str(t or ''), quote=True)
SIZES = '(max-width: 700px) 92vw, (max-width: 1040px) 46vw, 31vw'

def base_figures(s):
    r = block(s, 'works')
    if not r: return {}
    return {re.search(r'<img src="img/([^"?]+)', f).group(1): f for f in re.findall(r'<figure class="work".*?</figure>', s[r[0]:r[1]], re.S)}

def render_works(s, c):
    figs, out = base_figures(s), []
    for w in c['works']['added']:
        out.append(f'<figure class="work" data-cat="{E(w["cat"])}"><picture><source type="image/webp" srcset="img/{E(w["stem"])}-800.webp 800w, img/{E(w["stem"])}.webp {int(w["w"])}w" sizes="{SIZES}">'
                   f'<img src="img/{E(w["stem"])}.jpg" alt="{E(w["title"])}" loading="lazy"></picture><figcaption>{E(w["title"])}<span>{E(w["label"])}</span></figcaption></figure>')
    for w in site_data()['works']:
        f = figs.get(w['img'])
        if not f or w['img'] in c['works']['hidden']: continue
        ed = c['works']['edits'].get(w['img'])
        if ed:
            f = re.sub(r'alt="[^"]*"', f'alt="{E(ed["title"])}"', f, count=1)
            f = re.sub(r'<figcaption>.*?</figcaption>', f'<figcaption>{E(ed["title"])}<span>{E(ed["label"])}</span></figcaption>', f, count=1, flags=re.S)
            f = re.sub(r'data-cat="[^"]*"', f'data-cat="{E(ed["cat"])}"', f, count=1)
        out.append(f)
    return ''.join(out)

def render_clients(s, c):
    r = block(s, 'clients')
    if not r: return None
    items = re.findall(r'<li class="client.*?</li>', s[r[0]:r[1]], re.S)
    base = items[:len(items) // 3] if len(items) % 3 == 0 else items
    tiles = []
    for it in base:
        m = re.search(r'img/clients/([^"?]+)', it)
        if m and m.group(1) in c['clients']['hidden']: continue
        tiles.append(it)
    for cl in c['clients']['added']:
        tiles.append(f'<li class="client"><img src="img/clients/{E(cl["file"])}" alt="{E(cl["name"])}" style="width:{float(cl.get("width", 60)):.1f}%" draggable="false" decoding="async"></li>')
    dup = [re.sub(r'alt="[^"]*"', 'alt=""', t.replace('<li class="client', '<li aria-hidden="true" class="client', 1), count=1) for t in tiles]
    return ''.join(tiles) + ''.join(dup) + ''.join(dup)

def render_promo(c):
    pr = c['promo']
    if pr is None: return None
    if not pr.get('on'): return ''
    img = f'<img src="img/{E(pr["stem"])}.jpg" alt="{E(pr["alt"])}" width="{int(pr["w"])}" height="{int(pr["h"])}" decoding="async">'
    if pr.get('webp'): img = f'<picture><source type="image/webp" srcset="img/{E(pr["stem"])}.webp">{img}</picture>'
    return (f'<aside class="promo" id="promo" data-until="{E(pr["until"])}" aria-label="عرض خاص" hidden>\n  <div class="promo-bg"></div>\n'
            f'  <div class="promo-card"><button type="button" class="promo-x" aria-label="إخفاء العرض"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button>\n'
            f'    {img}</div>\n  <button type="button" class="promo-tab" aria-label="إظهار العرض"><span>{E(pr.get("tab") or "عرض خاص")}</span></button>\n</aside>\n')

def needed_files(c):
    """(version, path) of every uploaded file the current changes use."""
    out = []
    for path, im in c['images'].items(): out += [(im['v'], f) for f in im['files']]
    for w in c['works']['added']: out += [(w['v'], f) for f in w['files']]
    for cl in c['clients']['added']: out += [(cl['v'], f) for f in cl['files']]
    if c['promo'] and c['promo'].get('on') and c['promo'].get('v'): out += [(c['promo']['v'], f) for f in c['promo']['files']]
    for op in c.get('ops') or []:
        if op.get('v'): out += [(op['v'], f) for f in op['files']]
    return out

def apply(c=None):
    c = c or content()
    texts = c['texts']; imgs = c['images']
    # replaced photos: keep the release's original once, so taking a change back restores it
    for path, im in imgs.items():
        for f in im['files']:
            o, live = p('orig', f), os.path.join(SITE, f)
            if not os.path.exists(o) and os.path.exists(live):
                os.makedirs(os.path.dirname(o), exist_ok=True); shutil.copy2(live, o)
    for o in glob.glob(p('orig', 'img', '**', '*'), recursive=True):
        if os.path.isfile(o):
            rel = os.path.relpath(o, p('orig'))
            if not any(rel in im['files'] for im in imgs.values()):
                shutil.copy2(o, os.path.join(SITE, rel)); os.remove(o)
    for v, f in needed_files(c):
        src, dst = p('files', v, f), os.path.join(SITE, f)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); os.chmod(dst, 0o644)
    for name, _ in PAGES:
        try: write_text(os.path.join(SITE, name), render_page(name, c))
        except OSError: continue


# ---------------- free editing: add / copy / move / hide / link anywhere on a page ----------------
# The page is read as a tree of elements (start/end offsets). A spot is named by something stable inside it:
# a text key (data-e), a panel block (data-blk) or a photo (img src), plus how many levels up and which copy.
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
TAG_RE = re.compile(r'<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|<noscript\b.*?</noscript>|<(/?)([a-zA-Z][a-zA-Z0-9-]*)\b(?:[^>"\']|"[^"]*"|\'[^\']*\')*>', re.S)
def tree(s):
    nodes, stack = [], []
    for m in TAG_RE.finditer(s):
        if m.group(2) is None: continue
        tag = m.group(2).lower()
        if not m.group(1):
            nodes.append({'tag': tag, 'start': m.start(), 'oend': m.end(), 'end': m.end(), 'parent': stack[-1] if stack else None, 'open': m.group(0)})
            if tag not in VOID and not m.group(0).endswith('/>'): stack.append(len(nodes) - 1)
        else:
            for j in range(len(stack) - 1, -1, -1):
                if nodes[stack[j]]['tag'] == tag:
                    for k in stack[j + 1:]: nodes[k]['end'] = m.start()
                    nodes[stack[j]]['end'] = m.end(); del stack[j:]; break
    return nodes
def ident(n):
    o = n['open']
    m = re.search(r'\sdata-blk="([a-z0-9]+)"', o)
    if m: return ('blk', m.group(1))
    m = re.search(r'\sdata-e="([0-9a-f]{10})"', o)
    if m: return ('key', m.group(1))
    if n['tag'] == 'img':
        m = re.search(r'\ssrc="([^"?]+)', o)
        if m: return ('img', m.group(1))
    return None
def depth(nodes, i):
    d = 0
    while nodes[i]['parent'] is not None: i = nodes[i]['parent']; d += 1
    return d
def kids(nodes, i): return [k for k in range(i + 1, len(nodes)) if nodes[k]['parent'] == i]
def describe_node(nodes, i):
    """A stable name for element i: something inside it that has a name, else a named parent plus the way down."""
    n = nodes[i] if 0 <= i < len(nodes) else None
    if n and n['tag'] not in ('html', 'body', 'head') and not any(ident(nodes[j]) for j in range(i, len(nodes)) if nodes[j]['start'] < n['end']):
        path, a = [], i
        while a is not None and not ident(nodes[a]) and len(path) < 12:
            par = nodes[a]['parent']
            if par is None or nodes[par]['tag'] in ('html', 'body'): a = None; break
            path.insert(0, kids(nodes, par).index(a)); a = par
        if a is not None and ident(nodes[a]):
            idt = ident(nodes[a]); nth = sum(1 for k in range(a) if ident(nodes[k]) == idt)
            return {'by': idt[0], 'v': idt[1], 'up': 0, 'nth': nth, 'path': path}, i
    while i is not None:
        n = nodes[i]
        if n['tag'] in ('html', 'body', 'head'): return None, None
        j = i
        while j < len(nodes) and nodes[j]['start'] < n['end']:
            idt = ident(nodes[j])
            if idt:
                nth = sum(1 for k in range(j) if ident(nodes[k]) == idt)
                return {'by': idt[0], 'v': idt[1], 'up': depth(nodes, j) - depth(nodes, i), 'nth': nth}, i
            j += 1
        i = n['parent']
    return None, None
def resolve(nodes, t):
    hits = [k for k, n in enumerate(nodes) if ident(n) == (t['by'], t['v'])]
    if len(hits) <= t.get('nth', 0): return None
    i = hits[t.get('nth', 0)]
    for _ in range(t.get('up', 0)):
        i = nodes[i]['parent']
        if i is None: return None
    for k in t.get('path') or []:
        ks = kids(nodes, i)
        if k >= len(ks): return None
        i = ks[k]
    return i
URL_RE = re.compile(r'(https?://[^\s"<>]+|mailto:[^\s"<>]+|tel:[0-9+]+|/[^\s"<>]*|#[^\s"<>]*|[a-z-]+(#[^\s"<>]*)?)')
def safe_url(u):
    u = (u or '').strip()
    return u if len(u) <= 500 and URL_RE.fullmatch(u) else None
def set_link(s, n, href):
    """Point element n (or the first link / button inside it) at href."""
    nodes = tree(s[n['start']:n['end']])
    for k in nodes:
        if k['tag'] in ('a', 'button'): break
    else: return s
    a, b = n['start'] + k['start'], n['start'] + k['oend']
    o = s[a:b]
    ext = href.startswith('http')
    if k['tag'] == 'button':
        o = re.sub(r'^<button', '<a', o); o = re.sub(r'\s(type|data-copy)="[^"]*"', '', o)
        o = re.sub(r'(class="[^"]*?)\s*\bcopy\b', r'\1', o)  # the site would copy instead of opening the link
        end_a, end_b = n['start'] + k['end'] - len('</button>'), n['start'] + k['end']
        s = s[:end_a] + '</a>' + s[end_b:]
    o = re.sub(r'\s(href|target|rel)="[^"]*"', '', o)
    o = o[:-1] + f' href="{html.escape(href)}"' + (' target="_blank" rel="noopener"' if ext else '') + '>'
    return s[:a] + o + s[b:]
def apply_ops(s, name, ops):
    for op in ops:
        if op.get('page') != name: continue
        nodes = tree(s); i = resolve(nodes, op['target'])
        if i is None: continue
        n = nodes[i]
        if op['kind'] == 'insert':
            at = n['start'] if op['pos'] == 'before' else n['end']
            s = s[:at] + op['html'] + s[at:]
        elif op['kind'] == 'hide':
            s = s[:n['start']] + s[n['end']:]
        elif op['kind'] == 'link':
            s = set_link(s, n, op['href'])
        elif op['kind'] == 'move':
            sib = [k for k, x in enumerate(nodes) if x['parent'] == n['parent'] and k != i and x['tag'] not in ('script', 'style')]
            piece = s[n['start']:n['end']]
            if op['dir'] == 'up':
                prev = [k for k in sib if nodes[k]['end'] <= n['start']]
                if not prev: continue
                p0 = nodes[prev[-1]]['start']
                s = s[:p0] + piece + s[p0:n['start']] + s[n['end']:]
            else:
                nxt = [k for k in sib if nodes[k]['start'] >= n['end']]
                if not nxt: continue
                e1 = nodes[nxt[0]]['end']
                s = s[:n['start']] + s[n['end']:e1] + piece + s[e1:]
    return s
BAD_TAGS = re.compile(r'<(script|iframe|object|embed|style|link|meta|base|form)\b.*?(</\1>|>)', re.S | re.I)
def clean_html(h):
    h = BAD_TAGS.sub('', h or '')
    h = re.sub(r'\son[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', '', h, flags=re.I)
    h = re.sub(r'\s(href|src|action)\s*=\s*"\s*(javascript|data|vbscript):[^"]*"', r' \1="#"', h, flags=re.I)
    h = re.sub(r'\s(data-n|data-e|contenteditable|spellcheck|data-sel|data-hov)(="[^"]*")?', '', h)
    return h[:60000]
def snippet(s, n):
    t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(s[n['oend']:n['end']]))).strip()
    return t[:80]

def render_page(name, c):
    s = pristine(name)
    for key, new in c['texts'].items():
        for a, b in reversed(find_elements(s, key)): s = s[:a] + new + s[b:]
    if name == 'works.html' and block(s, 'works'): s = put_block(s, 'works', render_works(s, c))
    cl = render_clients(s, c)
    if cl is not None: s = put_block(s, 'clients', cl)
    promo = render_promo(c)
    if promo is not None: s = put_block(s, 'promo', promo)
    s = apply_ops(s, name, c.get('ops') or [])
    for path, im in c['images'].items():  # browsers keep photos for days; a new address makes them fetch the new one
        stem = re.escape(os.path.splitext(path)[0])
        s = re.sub(r'(%s(?:-\d+)?\.(?:jpg|jpeg|png|webp))(\?v=[0-9a-z]+)?(?=[\s"\',)])' % stem, r'\1?v=' + im['v'], s)
    return s

def render_preview(name, c):
    """The page as it would look with these (maybe unsaved) changes, inside the panel's preview frame."""
    s = render_page(name, c)
    for i, n in sorted(enumerate(tree(s)), key=lambda a: -a[1]['start']):  # the panel picks elements by this number
        if n['tag'] not in ('html', 'head', 'body', 'meta', 'link', 'title', 'base'):
            at = n['oend'] - (2 if n['open'].endswith('/>') else 1)
            s = s[:at] + f' data-n="{i}"' + s[at:]
    for v, f in needed_files(c):  # new photos are not on the site yet: the panel serves them
        s = re.sub(r'(?<=["\s,(])%s(\?v=[0-9a-z]+)?(?=[\s"\',)])' % re.escape(f), f'/admin/file/{v}/{f}', s)
    # no tracking from previews, and every relative address points at the live site
    s = re.sub(r'<script>window\.dataLayer.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<script>if\(/\(\^\|\\\.\)alhabibfactory.*?</script>', '', s, flags=re.S)
    m = re.search(r'id="promo" data-until="([0-9-]+)"', s)
    seen = f"<script>try{{localStorage.setItem('promo-seen-{m.group(1)}','1')}}catch(e){{}}</script>" if m else ''
    s = s.replace('<head>', '<head>\n<base href="/" target="_top">' + seen, 1)
    s = s.replace('</body>', PREVIEW_JS + '</body>', 1)
    return s
PREVIEW_JS = """<script>
var l = document.getElementById('loader'); if (l) l.remove();
document.addEventListener('click', function(e){ var a = e.target.closest('a'); if (!a) return; var h = a.getAttribute('href') || '';
  e.preventDefault(); var m = h.match(/^(?:\\/|\\.\\/)?([a-z-]*)(?:\\.html)?(?:#.*)?$/);
  if (m) parent.postMessage({go: (m[1] || 'index') + '.html'}, location.origin); }, true);
</script>"""

# ---------------- photos (Pillow) ----------------
def pil():
    try:
        from PIL import Image, ImageOps
        Image.MAX_IMAGE_PIXELS = 60_000_000
        return Image, ImageOps
    except ImportError:
        raise Fail('مكتبة الصور غير مثبتة على السيرفر. شغّل سطر التحديث مرة ثانية.')
class Fail(Exception): pass

def open_img(data):
    Image, ImageOps = pil()
    try:
        im = Image.open(io.BytesIO(data)); im.load(); im = ImageOps.exif_transpose(im)
    except Exception:
        raise Fail('الملف مو صورة أو نوعه غير مدعوم (استخدم JPG أو PNG أو WEBP)')
    return im
def fit(im, w):
    Image, _ = pil()
    if im.width <= w: return im
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
def rgb(im):
    Image, _ = pil()
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[-1]); return bg
    return im.convert('RGB')
def store(v, rel, im, fmt, **kw):
    dst = p('files', v, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, fmt, **kw); return rel

def process(kind, target, data):
    v = datetime.now().strftime('%y%m%d%H%M%S') + secrets.token_hex(2)
    im = open_img(data)
    if kind == 'replace':
        if not re.fullmatch(r'img/[a-z0-9_/-]+\.(jpg|png)', target) or '..' in target: raise Fail('صورة غير معروفة')
        stem, ext = os.path.splitext(target)
        orig = p('orig', target) if os.path.exists(p('orig', target)) else os.path.join(SITE, target)
        Image, _ = pil()
        try: ow = Image.open(orig).width
        except Exception: ow = 1600
        files = []
        if ext == '.jpg': files.append(store(v, target, rgb(fit(im, ow)), 'JPEG', quality=86, optimize=True, progressive=True))
        else: files.append(store(v, target, fit(im, ow).convert('RGBA'), 'PNG', optimize=True))
        for wf in sorted(glob.glob(os.path.join(SITE, glob.escape(stem) + '*'))):
            rel = os.path.relpath(wf, SITE); m = re.fullmatch(re.escape(stem) + r'(?:-(\d+))?\.(jpg|png|webp)', rel)
            if not m or rel == target: continue
            w = int(m.group(1)) if m.group(1) else ow
            if m.group(2) == 'webp': files.append(store(v, rel, fit(im, w), 'WEBP', quality=82, method=6))
            elif m.group(2) == 'jpg': files.append(store(v, rel, rgb(fit(im, w)), 'JPEG', quality=86, optimize=True, progressive=True))
            else: files.append(store(v, rel, fit(im, w).convert('RGBA'), 'PNG', optimize=True))
        return {'v': v, 'files': files}
    if kind == 'work':
        stem = 'work-u' + v
        big = rgb(fit(im, 1600))
        files = [store(v, f'img/{stem}.jpg', big, 'JPEG', quality=86, optimize=True, progressive=True),
                 store(v, f'img/{stem}.webp', big, 'WEBP', quality=82, method=6),
                 store(v, f'img/{stem}-800.webp', fit(big, 800), 'WEBP', quality=82, method=6)]
        return {'v': v, 'stem': stem, 'w': big.width, 'files': files}
    if kind == 'client':
        name = f'u{v}.png'; lg = fit(im.convert('RGBA'), 600)
        bb = lg.getbbox()
        if bb: lg = lg.crop(bb)
        ratio = lg.width / max(1, lg.height); width = min(80, (4400 * ratio) ** .5 / 188 * 100)
        return {'v': v, 'file': name, 'width': round(width, 1), 'files': [store(v, f'img/clients/{name}', lg, 'PNG', optimize=True)]}
    if kind == 'block':
        stem = 'blk-u' + v; b = rgb(fit(im, 1400))
        files = [store(v, f'img/{stem}.jpg', b, 'JPEG', quality=86, optimize=True, progressive=True),
                 store(v, f'img/{stem}.webp', b, 'WEBP', quality=82, method=6)]
        return {'v': v, 'stem': stem, 'w': b.width, 'h': b.height, 'files': files}
    if kind == 'promo':
        stem = 'promo-u' + v; pm = rgb(fit(im, 540))
        files = [store(v, f'img/{stem}.jpg', pm, 'JPEG', quality=86, optimize=True, progressive=True),
                 store(v, f'img/{stem}.webp', pm, 'WEBP', quality=82, method=6)]
        return {'v': v, 'stem': stem, 'w': pm.width, 'h': pm.height, 'webp': True, 'files': files}
    raise Fail('نوع غير معروف')

# ---------------- checking what the panel sends ----------------
FILE_RE = re.compile(r'img/[a-z0-9_/-]+\.(jpg|png|webp)')
V_RE = re.compile(r'[0-9a-f]{12,20}')
def files_ok(v, files):
    return isinstance(files, list) and V_RE.fullmatch(str(v)) and all(isinstance(f, str) and FILE_RE.fullmatch(f) and '..' not in f
                                                                      and os.path.exists(p('files', v, f)) for f in files)
def clean_content(new):
    old = content(); c = json.loads(json.dumps(EMPTY))
    known = editable_texts()
    for k, v in (new.get('texts') or {}).items():
        if k in known and isinstance(v, str):
            s = sanitize(v)
            if s and s != known[k]['html']: c['texts'][k] = s
    imgs = set(all_images())
    for k, im in (new.get('images') or {}).items():
        if k in imgs and isinstance(im, dict) and files_ok(im.get('v'), im.get('files')): c['images'][k] = {'v': im['v'], 'files': im['files']}
    cats = {k for k, _ in work_filters()}
    w = new.get('works') or {}
    for a in w.get('added') or []:
        if isinstance(a, dict) and files_ok(a.get('v'), a.get('files')) and re.fullmatch(r'work-u[0-9a-f]+', str(a.get('stem'))) and a.get('cat') in cats:
            c['works']['added'].append({'v': a['v'], 'files': a['files'], 'stem': a['stem'], 'w': int(a.get('w') or 1600),
                                        'title': str(a.get('title') or '')[:120], 'label': str(a.get('label') or '')[:80], 'cat': a['cat']})
    base = {x['img'] for x in site_data()['works']}
    c['works']['hidden'] = [x for x in (w.get('hidden') or []) if x in base]
    for k, ed in (w.get('edits') or {}).items():
        if k in base and isinstance(ed, dict) and ed.get('cat') in cats:
            c['works']['edits'][k] = {'title': str(ed.get('title') or '')[:120], 'label': str(ed.get('label') or '')[:80], 'cat': ed['cat']}
    cl = new.get('clients') or {}
    for a in cl.get('added') or []:
        if isinstance(a, dict) and files_ok(a.get('v'), a.get('files')) and re.fullmatch(r'u[0-9a-f]+\.png', str(a.get('file'))):
            c['clients']['added'].append({'v': a['v'], 'files': a['files'], 'file': a['file'], 'width': float(a.get('width') or 60), 'name': str(a.get('name') or '')[:120]})
    basec = {x['file'] for x in site_data()['clients']}
    c['clients']['hidden'] = [x for x in (cl.get('hidden') or []) if x in basec]
    for op in (new.get('ops') or [])[:400]:
        if not isinstance(op, dict) or op.get('page') not in NAMES or not re.fullmatch(r'[a-z0-9]{6,16}', str(op.get('id'))): continue
        t = op.get('target') or {}
        if t.get('by') not in ('key', 'blk', 'img') or not re.fullmatch(r'[a-z0-9/_.-]{1,200}', str(t.get('v'))): continue
        q = {'id': op['id'], 'page': op['page'], 'kind': op.get('kind'), 'label': str(op.get('label') or '')[:80],
             'target': {'by': t['by'], 'v': t['v'], 'up': max(0, min(30, int(t.get('up') or 0))), 'nth': max(0, min(500, int(t.get('nth') or 0)))}}
        if t.get('path'):
            if not isinstance(t['path'], list) or len(t['path']) > 12 or not all(isinstance(x, int) and 0 <= x <= 500 for x in t['path']): continue
            q['target']['path'] = t['path']
        if q['kind'] == 'insert':
            q['pos'] = 'before' if op.get('pos') == 'before' else 'after'
            h = clean_html(str(op.get('html') or ''))
            if not h.strip(): continue
            if f'data-blk="{op["id"]}"' not in h: h = re.sub(r'^\s*<([a-zA-Z0-9]+)', r'<\1 data-blk="%s"' % op['id'], h, count=1)
            q['html'] = h
            if op.get('v'):
                if not files_ok(op.get('v'), op.get('files')): continue
                q['v'], q['files'] = op['v'], op['files']
        elif q['kind'] == 'hide': pass
        elif q['kind'] == 'move': q['dir'] = 'up' if op.get('dir') == 'up' else 'down'
        elif q['kind'] == 'link':
            q['href'] = safe_url(op.get('href'))
            if not q['href']: continue
        else: continue
        c['ops'].append(q)
    pr = new.get('promo')
    if isinstance(pr, dict):
        if not pr.get('on'): c['promo'] = {'on': False}
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(pr.get('until'))) and re.fullmatch(r'promo(-u[0-9a-f]+)?', str(pr.get('stem'))):
            q = {'on': True, 'until': pr['until'], 'stem': pr['stem'], 'alt': str(pr.get('alt') or '')[:200], 'tab': str(pr.get('tab') or 'عرض خاص')[:30],
                 'w': int(pr.get('w') or 540), 'h': int(pr.get('h') or 960), 'webp': bool(pr.get('webp'))}
            if pr.get('v'):
                if not files_ok(pr.get('v'), pr.get('files')): raise Fail('صورة الإعلان ناقصة')
                q['v'], q['files'] = pr['v'], pr['files']
            c['promo'] = q
    return c

def all_images():
    out = []
    for name, _ in PAGES:
        try: s = pristine(name)
        except OSError: continue
        for m in re.finditer(r'<img [^>]*src="(img/[a-z0-9_/-]+\.(?:jpg|png))"', s):
            f = m.group(1)
            if f.startswith(('img/x/', 'img/clients/', 'img/promo')) or f in out: continue
            if re.match(r'img/work-', f): continue
            out.append(f)
    return out
def image_pages():
    out = {}
    for name, label in PAGES:
        try: s = pristine(name)
        except OSError: continue
        for f in set(re.findall(r'<img [^>]*src="(img/[a-z0-9_/-]+\.(?:jpg|png))"', s)): out.setdefault(f, []).append(name)
    return out

def work_filters():
    try: s = pristine('works.html')
    except OSError: return []
    names = dict(site_data().get('filters') or [])
    return [(k, names.get(k, k)) for k in re.findall(r'data-f="([a-z]+)"', s) if k != 'all']

def snapshot(c, note):
    os.makedirs(p('history'), exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    save_json(p('history', f'{ts}.json'), {'note': note, 'content': c})
    hs = sorted(glob.glob(p('history', '*.json')))
    for h in hs[:-80]: os.remove(h)

def history():
    out = []
    for h in sorted(glob.glob(p('history', '*.json')), reverse=True)[:80]:
        d = load(h, {}); n = os.path.basename(h)[:-5]
        out.append({'id': n, 'note': d.get('note', ''), 'at': datetime.strptime(n, '%Y%m%d-%H%M%S').strftime('%Y-%m-%d %H:%M')})
    return out

def describe(old, new):
    parts = []
    t = len(set(new['texts'].items()) ^ set(old['texts'].items()))
    if t: parts.append('تعديل نصوص')
    if new['images'] != old['images']: parts.append('تبديل صور')
    if new['works'] != old['works']: parts.append('أعمالنا')
    if new['clients'] != old['clients']: parts.append('العملاء')
    if new['promo'] != old['promo']: parts.append('الإعلان')
    if new.get('ops') != old.get('ops'): parts.append('تحرير حر')
    return '، '.join(parts) or 'حفظ'

def commit(new, note=None):
    with LOCK:
        old = content()
        if json.dumps(old, sort_keys=True) == json.dumps(new, sort_keys=True): return
        snapshot(old, 'قبل: ' + (note or describe(old, new)))
        save_json(p('content.json'), new)
        try: apply(new)
        except Exception:
            save_json(p('content.json'), old); apply(old); raise

# ---------------- visitors (from nginx's own log) ----------------
LOG_RE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) \S+ "([^"]*)" "([^"]*)"')
BOT_RE = re.compile(r'bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|curl|wget|python|httpclient|java/|go-http|headless|lighthouse|monitor|uptime|scan|okhttp|axios|node-fetch|whatsapp|telegram', re.I)
PAGE_RE = re.compile(r'^/(?:[a-z-]+(?:\.html)?)?/?$')
NAMES = dict(PAGES)
def source(ref, path):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
    u = (q.get('utm_source') or [''])[0].lower()
    host = urllib.parse.urlparse(ref).netloc.lower() if ref and ref != '-' else ''
    k = u or host
    for key, label in (('instagram', 'إنستقرام'), ('tiktok', 'تيك توك'), ('t.co', 'إكس'), ('twitter', 'إكس'), ('x.com', 'إكس'), ('snapchat', 'سناب شات'),
                       ('facebook', 'فيسبوك'), ('fb', 'فيسبوك'), ('google', 'قوقل'), ('bing', 'بينق'), ('linkedin', 'لينكدإن'), ('whatsapp', 'واتساب'), ('youtube', 'يوتيوب')):
        if key in k: return label
    if not k or DOMAIN in k: return 'مباشر'
    return k.replace('www.', '')[:40]
def refresh_stats():
    stats = load(p('stats.json'), {})
    days = {}
    for f in glob.glob(LOGS):
        try: fh = gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')
        except OSError: continue
        with fh:
            for line in fh:
                m = LOG_RE.match(line)
                if not m: continue
                ip, ts, meth, path, code, ref, ua = m.groups()
                if meth != 'GET' or code not in ('200', '304') or BOT_RE.search(ua) or not ua or ua == '-': continue
                clean = path.split('?')[0]
                if not PAGE_RE.match(clean) or clean.startswith('/admin'): continue
                try: d = datetime.strptime(ts.split()[0], '%d/%b/%Y:%H:%M:%S').date().isoformat()
                except ValueError: continue
                page = clean.strip('/').replace('.html', '') or 'index'
                vid = hashlib.sha1((ip + ua).encode()).hexdigest()[:8]
                day = days.setdefault(d, {'v': set(), 'pv': 0, 'pages': {}, 'src': {}})
                day['pv'] += 1; day['pages'][page] = day['pages'].get(page, 0) + 1
                if vid not in day['v']:
                    day['v'].add(vid); s = source(ref, path); day['src'][s] = day['src'].get(s, 0) + 1
    for d, x in days.items():
        stats[d] = {'v': sorted(x['v']), 'pv': x['pv'], 'pages': x['pages'], 'src': x['src']}
    keep = (date.today() - timedelta(days=400)).isoformat()
    stats = {d: x for d, x in stats.items() if d >= keep}
    save_json(p('stats.json'), stats)
    return stats
def stats_summary():
    st = refresh_stats(); today = date.today()
    def span(n):
        ds = [(today - timedelta(days=i)).isoformat() for i in range(n)]
        v, pv, pages, src = set(), 0, {}, {}
        for d in ds:
            x = st.get(d)
            if not x: continue
            v.update(x['v']); pv += x['pv']
            for k, c in x['pages'].items(): pages[k] = pages.get(k, 0) + c
            for k, c in x['src'].items(): src[k] = src.get(k, 0) + c
        return {'visitors': len(v), 'views': pv, 'pages': sorted(pages.items(), key=lambda a: -a[1])[:10], 'sources': sorted(src.items(), key=lambda a: -a[1])[:10]}
    daily = [{'d': (today - timedelta(days=i)).isoformat(), 'v': len(st.get((today - timedelta(days=i)).isoformat(), {}).get('v', []))} for i in range(29, -1, -1)]
    first = min(st) if st else None
    return {'today': span(1), 'week': span(7), 'month': span(30), 'daily': daily, 'since': first,
            'names': {k.replace('.html', ''): v for k, v in NAMES.items()}}

# ---------------- login ----------------
def auth(): return load(p('admin.json'), {})
def check_password(user, pw):
    a = auth()
    if not a.get('hash'): return False
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(a['salt']), 200000).hex()
    return hmac.compare_digest(h, a['hash']) and hmac.compare_digest(user.strip().lower(), a['user'])
SESSIONS = {}; TRIES = {}; DRAFTS = {}
def new_session():
    t = secrets.token_urlsafe(32); SESSIONS[t] = time.time() + 12 * 3600; return t

# ---------------- web ----------------
class H(http.server.BaseHTTPRequestHandler):
    server_version = 'alhabib-admin'
    def log_message(self, *a): pass
    def ip(self): return self.headers.get('X-Real-IP') or self.client_address[0]
    def session(self):
        m = re.search(r'(?:^|;\s*)ah_s=([A-Za-z0-9_-]+)', self.headers.get('Cookie', ''))
        t = m and m.group(1)
        if t and SESSIONS.get(t, 0) > time.time(): return t
        return None
    def send(self, code, body, ctype='application/json; charset=utf-8', headers=(), frame=False):
        if not isinstance(body, bytes): body = (json.dumps(body, ensure_ascii=False) if 'json' in ctype else body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Frame-Options', 'SAMEORIGIN' if frame else 'DENY')
        self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Referrer-Policy', 'same-origin')
        if frame:  # the preview page: the site's own files only, no outside scripts, shown only inside the panel
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; connect-src 'self'; frame-ancestors 'self'")
        else:
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; frame-src 'self'; frame-ancestors 'none'")
        for k, v in headers: self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)
    def body(self, limit):
        n = int(self.headers.get('Content-Length') or 0)
        if n > limit: raise Fail('الملف كبير، الحد %d ميقا' % (limit // 1_000_000))
        return self.rfile.read(n)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); path = u.path.rstrip('/'); q = urllib.parse.parse_qs(u.query)
        if path == '/admin':
            return self.send(200, PAGE, 'text/html; charset=utf-8')
        if not self.session(): return self.send(401, {'error': 'login'})
        try:
            if path == '/admin/api/state':
                c = content(); texts = editable_texts(); ip_ = image_pages()
                return self.send(200, {'content': c, 'texts': texts, 'pages': PAGES, 'images': [{'path': f, 'pages': ip_.get(f, [])} for f in all_images()],
                                       'works': site_data()['works'], 'filters': work_filters(), 'clients': site_data()['clients'],
                                       'promo': site_data().get('promo'), 'history': history()})
            if path == '/admin/api/stats': return self.send(200, stats_summary())
            if path in ('/admin/api/target', '/admin/api/copy'):
                name = (q.get('page') or [''])[0]; idx = int((q.get('n') or ['-1'])[0])
                if name not in NAMES: raise Fail('صفحة غير معروفة')
                c = DRAFTS.get(self.session()) or content(); s = render_page(name, c); nodes = tree(s)
                if not 0 <= idx < len(nodes): raise Fail('اختر مكان بالمعاينة')
                d, i = describe_node(nodes, idx)
                if not d: raise Fail('هذا المكان ما ينفع نحدده، اختر عنصر أصغر')
                n = nodes[i]; blk = None; k = i
                while k is not None:
                    m2 = re.search(r'\sdata-blk="([a-z0-9]+)"', nodes[k]['open'])
                    if m2: blk = m2.group(1); break
                    k = nodes[k]['parent']
                if path == '/admin/api/copy':
                    piece = re.sub(r'\sdata-(e|blk|bi)="[^"]*"', '', s[n['start']:n['end']])
                    return self.send(200, {'html': piece})
                ce = f"</{n['tag']}>"; inner = s[n['oend']:n['end'] - len(ce)] if s[n['end'] - len(ce):n['end']].lower() == ce else s[n['oend']:n['end']]
                return self.send(200, {'target': d, 'n': i, 'tag': n['tag'], 'text': snippet(s, n), 'blk': blk,
                                       'key': d['v'] if d['by'] == 'key' and d['up'] == 0 and not d.get('path') else None,
                                       'textonly': not re.search(r'<(?!/?(br|em|b|strong|i|u|span|bdi|small)\b)[a-zA-Z/]', inner),
                                       'link': bool(re.search(r'<(a|button)\b', s[n['start']:n['end']]))})
            m = re.fullmatch(r'/admin/preview/([a-z-]+\.html)', path)
            if m and m.group(1) in NAMES:
                c = DRAFTS.get(self.session()) or content()
                return self.send(200, render_preview(m.group(1), c), 'text/html; charset=utf-8', frame=True)
            m = re.fullmatch(r'/admin/file/([0-9a-f]{12,20})/(img/[a-z0-9_/-]+\.(jpg|png|webp))', path)
            if m and '..' not in path and os.path.exists(p('files', m.group(1), m.group(2))):
                with open(p('files', m.group(1), m.group(2)), 'rb') as f: data = f.read()
                return self.send(200, data, {'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}[m.group(3)])
        except Fail as e: return self.send(400, {'error': str(e)})
        self.send(404, {'error': 'not found'})
    def do_POST(self):
        u = urllib.parse.urlparse(self.path); path = u.path; q = urllib.parse.parse_qs(u.query)
        # cross-site forms cannot send this header, so every change comes from the panel itself
        if self.headers.get('X-Panel') != '1': return self.send(403, {'error': 'forbidden'})
        try:
            if path == '/admin/api/login':
                now = time.time(); ip = self.ip()
                TRIES[ip] = [t for t in TRIES.get(ip, []) if t > now - 900]
                if len(TRIES[ip]) >= 8: return self.send(429, {'error': 'محاولات كثيرة، جرّب بعد ربع ساعة'})
                d = json.loads(self.body(10_000) or b'{}')
                if not auth().get('hash'): return self.send(400, {'error': 'nopass'})
                if not check_password(str(d.get('user', '')), str(d.get('pass', ''))):
                    TRIES[ip].append(now); time.sleep(1); return self.send(401, {'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'})
                return self.send(200, {'ok': True}, headers=[('Set-Cookie', f'ah_s={new_session()}; Path=/admin; Max-Age=43200; HttpOnly; Secure; SameSite=Strict')])
            t = self.session()
            if not t: return self.send(401, {'error': 'login'})
            if path == '/admin/api/logout':
                SESSIONS.pop(t, None)
                return self.send(200, {'ok': True}, headers=[('Set-Cookie', 'ah_s=; Path=/admin; Max-Age=0; HttpOnly; Secure; SameSite=Strict')])
            if path == '/admin/api/save':
                new = clean_content(json.loads(self.body(2_000_000)))
                commit(new); return self.send(200, {'ok': True, 'content': content(), 'history': history()})
            if path == '/admin/api/draft':
                DRAFTS[t] = clean_content(json.loads(self.body(2_000_000))); return self.send(200, {'ok': True})
            if path == '/admin/api/upload':
                kind = (q.get('kind') or [''])[0]; target = (q.get('path') or [''])[0]
                with LOCK: r = process(kind, target, self.body(25_000_000))
                return self.send(200, r)
            if path == '/admin/api/restore':
                hid = (q.get('id') or [''])[0]
                if not re.fullmatch(r'\d{8}-\d{6}', hid): raise Fail('نسخة غير معروفة')
                d = load(p('history', hid + '.json'), None)
                if not d: raise Fail('النسخة غير موجودة')
                commit(clean_content(d['content']), 'استرجاع نسخة ' + hid)
                return self.send(200, {'ok': True, 'content': content(), 'history': history()})
        except Fail as e: return self.send(400, {'error': str(e)})
        except (ValueError, KeyError, TypeError) as e: return self.send(400, {'error': 'طلب غير صحيح'})
        self.send(404, {'error': 'not found'})

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

PAGE = ''
def main():
    global PAGE
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'admin.html'), encoding='utf-8') as f: PAGE = f.read()
    Server(('127.0.0.1', PORT), H).serve_forever()

def set_password():
    user = input('اسم المستخدم للوحة (مثلاً admin): ').strip().lower() or 'admin'
    while True:
        a = getpass.getpass('كلمة المرور (8 أحرف على الأقل، ما تظهر وانت تكتب): ')
        if len(a) < 8: print('قصيرة، 8 أحرف على الأقل'); continue
        if getpass.getpass('اكتبها مرة ثانية: ') != a: print('ما تطابقت، جرّب مرة ثانية'); continue
        break
    salt = secrets.token_bytes(16)
    save_json(p('admin.json'), {'user': user, 'salt': salt.hex(), 'hash': hashlib.pbkdf2_hmac('sha256', a.encode(), salt, 200000).hex()})
    os.chmod(p('admin.json'), 0o600)
    try: shutil.chown(p('admin.json'), 'alhabib', 'alhabib')
    except (LookupError, OSError): pass
    print(f'تم. ادخل على https://{DOMAIN}/admin باسم المستخدم: {user}')

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg == '--password': set_password()
    elif arg == '--apply': apply(); print('changes applied')
    elif arg == '--stats': refresh_stats(); print('stats updated')
    elif arg == '': main()
    else: print('unknown option. use: --password, --apply or --stats'); sys.exit(2)
