"""Turn a raw project video into web clips for the works page.

usage: python vproc.py IN.mp4 OUTDIR SLUG [--max 16] [--skip-head 0.3] [--skip-tail 1.5]

Writes OUTDIR/SLUG.mp4 (highlight, cleaned up, H.264 faststart, with sound when there is any),
OUTDIR/SLUG-loop.mp4 (short muted 9:16 loop for the card) and OUTDIR/SLUG.jpg (poster = first
frame of the loop). Shots are found with ffmpeg scene detection; the sharpest, best-exposed shots
are kept in their original order until the highlight reaches --max seconds. Every file stays
under the artifact host's 15 MB per-file limit.
"""
import os, re, json, math, subprocess, argparse
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
MAX_BYTES = 14.5e6
TAGS_709 = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']


def run(args, **kw):
    return subprocess.run([FF, '-hide_banner', '-nostdin', '-y'] + args, capture_output=True, text=True, **kw)


def hms(m):
    return int(m[0]) * 3600 + int(m[1]) * 60 + float(m[2])


def probe(path):
    err = run(['-i', path]).stderr
    dur = hms(re.search(r'Duration: (\d+):(\d+):([\d.]+)', err).groups())
    v = re.search(r'Video: .*?, (\d{2,5})x(\d{2,5})', err)
    rot = re.search(r'rotation of (-?[\d.]+)', err) or re.search(r'rotate\s*:\s*(-?\d+)', err)
    w, h = int(v[1]), int(v[2])
    if rot and abs(float(rot[1])) % 180 == 90:
        w, h = h, w
    fps = re.search(r'([\d.]+) fps', err)
    fps = float(fps[1]) if fps else 30.0
    # the container duration can outlast the video track (audio tail); clamp to real video
    m = re.findall(r'time=(\d+):(\d+):([\d.]+)', run(['-i', path, '-map', '0:v:0', '-c', 'copy', '-f', 'null', '-']).stderr)
    if m:
        dur = min(dur, hms(m[-1]) + 1 / fps)
    return {'dur': dur, 'w': w, 'h': h, 'fps': fps, 'audio': 'Audio:' in err,
            'hdr': bool(re.search(r'arib-std-b67|smpte2084', err))}


def cuts(path, thresh=0.32):
    err = run(['-i', path, '-vf', f"select='gt(scene,{thresh})',showinfo", '-an', '-f', 'null', '-']).stderr
    return [float(t) for t in re.findall(r'pts_time:([\d.]+)', err)]


def frame_stats(path, fps=4, w=160):
    """Sharpness (Laplacian variance) and mean luma per sampled frame."""
    info = probe(path)
    h = int(round(w * info['h'] / info['w'] / 2)) * 2
    p = subprocess.run([FF, '-v', 'error', '-i', path, '-vf', f'fps={fps},scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)
    lap = a[:, 1:-1, 1:-1] * 4 - a[:, :-2, 1:-1] - a[:, 2:, 1:-1] - a[:, 1:-1, :-2] - a[:, 1:-1, 2:]
    sharp = lap.reshape(len(a), -1).var(1)
    luma = a.reshape(len(a), -1).mean(1)
    t = np.arange(len(a)) / fps
    return t, sharp, luma


def pick(path, max_len, skip_head, skip_tail):
    info = probe(path)
    d, frame = info['dur'], 1 / info['fps']
    lo, hi = skip_head, max(skip_head + 1, d - skip_tail)
    cs = cuts(path)
    # a cut just inside the trimmed edges becomes the edge, so no sliver of that shot survives
    near_lo = [c for c in cs if lo < c <= lo + .6]
    near_hi = [c for c in cs if hi - .6 <= c < hi]
    if near_lo: lo = max(near_lo)
    if near_hi: hi = min(near_hi)
    bounds = [lo] + [c for c in cs if lo + .6 < c < hi - .6] + [hi]
    t, sharp, luma = frame_stats(path)
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        b = b - 0.5 * frame  # end strictly before the cut frame
        if b - a < 1.0:
            continue
        m = (t >= a) & (t < b)
        if not m.any():
            continue
        s = float(np.median(sharp[m]))
        l = float(np.median(luma[m]))
        expo = 1.0 - min(1.0, abs(l - 120) / 120)  # penalise very dark / blown shots
        shots.append({'a': a, 'b': b, 'score': s * (.4 + .6 * expo)})
    if not shots:
        return [(lo, min(hi, lo + max_len))], info
    per = 4.0 if len(shots) > 2 else max_len  # long single takes keep more
    chosen, total = [], 0.0
    for s in sorted(shots, key=lambda s: -s['score']):
        seg = min(per, s['b'] - s['a'], max_len - total)
        if seg < 1.0:
            break
        mid = (s['a'] + s['b']) / 2
        a = max(s['a'], mid - seg / 2)
        chosen.append((a, a + seg))
        total += seg
        if total >= max_len - 0.05:
            break
    chosen.sort()
    return chosen, info


def enhance_chain(info, target_long=1920):
    """Tone-map HDR, denoise, fit to 1920 on the long side, and sharpen only when upscaling."""
    w, h = info['w'], info['h']
    f = []
    if info['hdr']:
        f.append('zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:param=0.6:desat=0,'
                 'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')
    f.append('hqdn3d=3:2:6:4')
    f.append(f'scale=-2:{target_long}:flags=lanczos' if h >= w else f'scale={target_long}:-2:flags=lanczos')
    if max(w, h) < target_long:
        f.append('cas=0.3')
    f.append('eq=contrast=1.04:saturation=1.06')
    f.append('format=yuv420p')
    return ','.join(f)


def loudness(parts, n):
    """Integrated loudness of the concatenated audio (LUFS) plus loudnorm's measured values, or None."""
    fc = ';'.join(f'[{i}:a]asetpts=PTS-STARTPTS,aresample=48000[a{i}]' for i in range(n))
    fc += ';' + ''.join(f'[a{i}]' for i in range(n)) + f'concat=n={n}:v=0:a=1,loudnorm=I=-16:TP=-1.5:print_format=json[ao]'
    err = run(parts + ['-filter_complex', fc, '-map', '[ao]', '-f', 'null', '-']).stderr
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', err)
    if not m:
        return None
    j = json.loads(m[0])
    try:
        return {k: float(j[k]) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')}
    except (KeyError, ValueError):
        return None


def encode(parts, fc, maps, out, vk, two_pass_kbps=None):
    common = parts + ['-filter_complex', ';'.join(fc)] + maps
    vopts = ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p'] + TAGS_709
    if two_pass_kbps:
        log = out + '.2pass'
        r = run(common + vopts + ['-b:v', f'{two_pass_kbps}k', '-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', os.devnull])
        if r.returncode:
            raise SystemExit(r.stderr[-2000:])
        r = run(common + vopts + ['-b:v', f'{two_pass_kbps}k', '-pass', '2', '-passlogfile', log, '-movflags', '+faststart', '-shortest', out])
        for f in os.listdir(os.path.dirname(out) or '.'):
            if f.startswith(os.path.basename(log)):
                os.remove(os.path.join(os.path.dirname(out) or '.', f))
    else:
        r = run(common + vopts + ['-crf', '22', '-maxrate', f'{vk}k', '-bufsize', f'{2 * vk}k', '-movflags', '+faststart', '-shortest', out])
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


def build(path, outdir, slug, max_len=16, skip_head=0.3, skip_tail=1.5, loop_len=5):
    os.makedirs(outdir, exist_ok=True)
    segs, info = pick(path, max_len, skip_head, skip_tail)
    chain = enhance_chain(info)
    n = len(segs)
    parts = []
    for a, b in segs:
        a3 = math.ceil(a * 1000) / 1000
        parts += ['-ss', f'{a3:.3f}', '-t', f'{math.floor((b - a3) * 1000) / 1000:.3f}', '-i', path]
    total = sum(math.floor((b - math.ceil(a * 1000) / 1000) * 1000) / 1000 for a, b in segs)

    # audio: keep real sound at a sane level; near-silent tracks are not boosted into hiss
    au = loudness(parts, n) if info['audio'] else None
    has_a = info['audio']
    if au and au['input_i'] >= -35:
        norm = (f"loudnorm=I=-16:TP=-1.5:measured_I={au['input_i']}:measured_TP={au['input_tp']}:measured_LRA={au['input_lra']}"
                f":measured_thresh={au['input_thresh']}:offset={au['target_offset']}:linear=true,")
    else:
        norm = ''
    fc = []
    for i in range(n):
        fc.append(f'[{i}:v]setpts=PTS-STARTPTS,fps=30[v{i}]')
        if has_a:
            fc.append(f'[{i}:a]asetpts=PTS-STARTPTS,aresample=48000[a{i}]')
    if has_a:
        fc.append(''.join(f'[v{i}][a{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=1[vc][ac]')
    else:
        fc.append(''.join(f'[v{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[vc]')
    # an unfaded copy feeds the card loop; the highlight itself fades in and out
    fc.append(f'[vc]{chain},split[vx][vl]')
    fc.append(f'[vx]fade=t=in:st=0:d=0.35,fade=t=out:st={max(0, total - .45):.2f}:d=0.45[vo]')
    if has_a:
        fc.append(f'[ac]{norm}afade=t=in:st=0:d=0.3,afade=t=out:st={max(0, total - .5):.2f}:d=0.5,aresample=48000[ao]')
    out = os.path.join(outdir, slug + '.mp4')
    clean = os.path.join(outdir, slug + '.clean.mp4')
    amaps = ['-map', '[ao]', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000'] if has_a else ['-an']
    abits = 130 if has_a else 0
    vk = max(1500, min(6000, int((14.0 * 8192 - abits * total) / max(total, 1))))
    # write the highlight and a high-quality unfaded twin in one pass
    common_v = ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p'] + TAGS_709
    r = run(parts + ['-filter_complex', ';'.join(fc), '-map', '[vo]'] + amaps + common_v +
            ['-crf', '22', '-maxrate', f'{vk}k', '-bufsize', f'{2 * vk}k', '-movflags', '+faststart', '-shortest', out,
             '-map', '[vl]', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-pix_fmt', 'yuv420p'] + TAGS_709 + [clean])
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    if os.path.getsize(out) > MAX_BYTES:
        kbps = int((13.5 * 8192 - abits * total) / max(total, 1))
        fc2 = [x for x in fc if not x.startswith('[vx]')]
        fc2 = [x.replace(',split[vx][vl]', '[vx]') if x.startswith('[vc]') else x for x in fc2]
        fc2.append(f'[vx]fade=t=in:st=0:d=0.35,fade=t=out:st={max(0, total - .45):.2f}:d=0.45[vo]')
        encode(parts, fc2, ['-map', '[vo]'] + amaps, out, vk, two_pass_kbps=kbps)

    # muted 9:16 loop from the sharpest stretch of the unfaded twin, clear of the edges
    t, sharp, _ = frame_stats(clean)
    vtotal = len(t) / 4
    k = int(np.argmax(np.convolve(sharp, np.ones(8) / 8, 'same')))
    lo_e, hi_e = 0.2, vtotal - 0.2
    L = min(loop_len, hi_e - lo_e)
    la = min(max(t[k] - L / 2, lo_e), hi_e - L)
    loop = os.path.join(outdir, slug + '-loop.mp4')
    scale = 'scale=-2:960' if info['h'] >= info['w'] else 'crop=ih*9/16:ih,scale=540:960'
    r = run(['-ss', f'{la:.2f}', '-t', f'{L:.2f}', '-i', clean, '-an', '-vf', f'{scale}:flags=lanczos,format=yuv420p',
             '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-maxrate', '1800k', '-bufsize', '3600k'] + TAGS_709 +
            ['-movflags', '+faststart', loop])
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    os.remove(clean)
    poster = os.path.join(outdir, slug + '.jpg')
    run(['-i', loop, '-frames:v', '1', '-q:v', '3', poster])
    for p in (out, loop, poster):
        assert os.path.getsize(p) <= 15e6, f'{p} is over 15 MB'
    meta = {'slug': slug, 'src': os.path.basename(path), 'segments': segs, 'dur': round(total, 2),
            'w': info['w'], 'h': info['h'], 'portrait': info['h'] > info['w'], 'hdr': info['hdr'],
            'audio': has_a, 'loudness_in': au and au['input_i'],
            'sizes_kb': {os.path.basename(p): os.path.getsize(p) // 1024 for p in (out, loop, poster)}}
    json.dump(meta, open(os.path.join(outdir, slug + '.json'), 'w'), ensure_ascii=False, indent=1)
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('outdir'); ap.add_argument('slug')
    ap.add_argument('--max', type=float, default=16)
    ap.add_argument('--skip-head', type=float, default=0.3)
    ap.add_argument('--skip-tail', type=float, default=1.5)
    a = ap.parse_args()
    print(json.dumps(build(a.inp, a.outdir, a.slug, a.max, a.skip_head, a.skip_tail), ensure_ascii=False))
