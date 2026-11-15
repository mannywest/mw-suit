#!/usr/bin/env python3
"""Ingest a fabric-book PDF into public/fabrics: crop, flatten, mirror-tile, read label code, write manifest.json.
Usage: python3 tools/ingest.py book.pdf [--supplier "Den Vi"] [--book "Stylish100 5822"] [--out public/fabrics]
Needs: poppler (pdfimages), tesseract, python: pillow numpy opencv-python."""
import argparse, json, os, re, subprocess, sys, tempfile, glob
import numpy as np, cv2
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser(); ap.add_argument('pdf'); ap.add_argument('--supplier', default='Den Vi'); ap.add_argument('--book', default='Stylish100 5822')
ap.add_argument('--out', default='public/fabrics'); a = ap.parse_args()
CROP = (290, 880, 990, 1580)   # cloth area on a 1279x1706 page (below label, away from ruler/edges)
PX_PER_MM = 8.27               # ~210 px/in measured on a ruler page; unverified per page
os.makedirs(a.out, exist_ok=True)
tmp = tempfile.mkdtemp(); subprocess.run(['pdfimages', '-j', a.pdf, tmp + '/p'], check=True, capture_output=True)
pages = sorted(glob.glob(tmp + '/p-*.jpg'))

def label(img):
    g = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY); h, w = g.shape
    top = (g[: int(h * .45)] > 185).astype('uint8')
    top = cv2.morphologyEx(top, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(top)
    best = None
    for i in range(1, n):
        x, y, bw, bh, ar = st[i]
        if 150 < bw < 500 and 80 < bh < 400 and ar > .5 * bw * bh and (best is None or ar > best[4]): best = (x, y, bw, bh, ar)
    if not best: return None, None, None
    x, y, bw, bh, _ = best; crop = img.crop((x, y, x + bw, y + bh))
    txt = ''
    gray = cv2.cvtColor(np.asarray(crop), cv2.COLOR_RGB2GRAY)
    variants = [cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
                cv2.threshold(cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                cv2.adaptiveThreshold(cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 15)]
    code = wt = None
    for v in variants:
        for psm in ('6', '11'):
            cv2.imwrite(tmp + '/l.png', v)
            t = subprocess.run(['tesseract', tmp + '/l.png', '-', '--psm', psm], capture_output=True, text=True).stdout
            code = code or re.search(r'(\d{4})\s*[-–—~_.]\s*(\d{4})', t); wt = wt or re.search(r'(\d{3})\s*g', t, re.I)
        if code and wt: break
    if wt and not 250 <= int(wt.group(1)) <= 450: wt = None
    return (f'{code.group(1)}-{code.group(2)}' if code else None), (int(wt.group(1)) if wt else None), crop

fabrics = []
for i, f in enumerate(pages, 1):
    img = Image.open(f).convert('RGB'); code, wt, lab = label(img)
    c = img.crop(CROP).resize((512, 512), Image.LANCZOS); arr = np.asarray(c, float)
    lum = arr.mean(); g = np.asarray(c.convert('L'), float)
    mid = np.asarray(c.convert('L').filter(ImageFilter.GaussianBlur(3)), float) - np.asarray(c.convert('L').filter(ImageFilter.GaussianBlur(40)), float)
    patterned = bool(mid.std() > 6)
    flags = []
    if (g > 170).mean() > .02: flags.append('bright-pixels(ruler/label in crop?)')
    if code is None: flags.append('no-label-code')
    sg = 70 if patterned else 12
    bl = np.asarray(c.filter(ImageFilter.GaussianBlur(sg)), float); m = arr.reshape(-1, 3).mean(0)
    gain = float(np.clip(55 / max(lum, 1), 1, 1.8))
    out = np.clip(m * gain + (arr - bl) * gain * 1.2, 0, 255) if not patterned else np.clip(arr / np.maximum(bl, 1) * m * gain, 0, 255)
    t = Image.new('RGB', (1024, 1024)); c2 = Image.fromarray(out.astype('uint8'))
    t.paste(c2, (0, 0)); t.paste(c2.transpose(Image.FLIP_LEFT_RIGHT), (512, 0)); t.paste(c2.transpose(Image.FLIP_TOP_BOTTOM), (0, 512)); t.paste(c2.transpose(Image.ROTATE_180), (512, 512))
    fid = f'p{i:02d}'; t.save(f'{a.out}/{fid}.jpg', quality=68, optimize=True)
    th = t.resize((96, 96)); th.save(f'{a.out}/{fid}_t.jpg', quality=70)
    mean = out.reshape(-1, 3).mean(0)
    hue = ('light' if mean.mean() > 110 else 'dark') 
    r, g_, b = mean; fam = 'grey' if max(r, g_, b) - min(r, g_, b) < 10 else ('blue' if b >= max(r, g_) else ('green' if g_ >= max(r, b) else 'red/brown'))
    fabrics.append(dict(id=fid, code=code, name=(f'{code} ' if code else f'Page {i} ') + ('pattern' if patterned else 'plain') + f' {fam}', supplier=a.supplier, book=a.book, page=i,
        weightGsm=wt, pattern='patterned' if patterned else 'plain', family=fam, tone=hue, file=f'fabrics/{fid}.jpg', thumb=f'fabrics/{fid}_t.jpg',
        tileCm=round(2 * 700 / PX_PER_MM / 10, 1), scaleVerified=False, review=flags, source=f'{a.supplier} {a.book}, book page {i}'))
    print(i, code, wt, 'pat' if patterned else 'plain', fam, flags)
from collections import Counter
cnt = Counter(x['code'] for x in fabrics if x['code'])
for x in fabrics:
    if x['code'] and cnt[x['code']] > 1: x['review'].append('duplicate-code')
json.dump(dict(version=2, fabrics=fabrics), open(f'{a.out}/manifest.json', 'w'), indent=1)
print('wrote', len(fabrics))
