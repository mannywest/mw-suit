#!/usr/bin/env python3
"""
One-command check for the MW Tailleur suit GLB.

    python3 scripts/check_all.py NEW.glb [PREVIOUS.glb]

Runs the same neck-area checks used in the 15 Nov 2026 repair work, on the NEW file and (if given) the
PREVIOUS file, then prints one short table: Fixed / Same / Made worse / Clean.

  holes_<dir>   see-through pixels at the neck, viewed from 6 directions (same method as scripts/check/gapview.py)
  holes_total   sum of the six
  shirt_poke    mm2 of shirt showing above the jacket round the collar (same method as scripts/cloud/shirt_poke.py)
  validator     errors reported by tools/validate.js (gltf-validator; run `npm install` in tools/ once)

Works on the repair GLBs in the repo root (plain float data). It does not read the meshopt-compressed
copies under configurator/public/models. Finds parts by material name (Jacket_Wool, Jacket_Lapel*), so it
does not depend on primitive order or on any Mac path.

Not covered (still needs eyes): close-up renders, flat "ears" over the shoulders, odd shapes. A low count
is necessary, not sufficient.
"""
import sys, os, re, json, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    from pygltflib import GLTF2
    from scipy import ndimage as ndi
except ImportError:
    sys.exit('Needs: pip install pygltflib numpy scipy')

DTYPE = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}
DIRS = ['0,0,-1', '0.8,0,-1', '-0.8,0,-1', '0,0.6,-1', '0.8,0,1', '-0.8,0,1']


def _read(g, blob, acc_id, ncomp, dtype):
    a = g.accessors[acc_id]; bv = g.bufferViews[a.bufferView]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    size = np.dtype(dtype).itemsize; st = bv.byteStride or ncomp * size
    raw = np.frombuffer(blob, dtype=np.uint8)
    idx = off + np.arange(a.count)[:, None] * st + np.arange(ncomp * size)[None, :]
    return raw[idx].copy().view(dtype).reshape(a.count, ncomp)


def load(path):
    g = GLTF2().load(path); blob = g.binary_blob()
    if any('EXT_meshopt' in (e or '') for e in (g.extensionsUsed or [])):
        sys.exit(f'{os.path.basename(path)}: meshopt-compressed; use the repair GLBs in the repo root')
    def prim_info(p):
        name = g.materials[p.material].name if p.material is not None else ''
        pos = _read(g, blob, p.attributes.POSITION, 3, '<f4').astype(float)
        idx = _read(g, blob, p.indices, 1, DTYPE[g.accessors[p.indices].componentType]).reshape(-1, 3).astype(int)
        return name, pos, idx
    parts = {}
    for m in g.meshes:
        for p in m.primitives:
            nm, pos, idx = prim_info(p); parts.setdefault((m.name, nm), (pos, idx))
    return parts


def merge(items):
    P = []; F = []; off = 0
    for pos, idx in items:
        P.append(pos); F.append(idx + off); off += len(pos)
    return np.vstack(P), np.vstack(F)


def depthmap(P, F, box, W, H):
    u0, u1, v0, v1 = box; s = W / (u1 - u0)
    X = (-P[:, 0] - u0) * s; Y = (v1 - P[:, 1]) * s; Z = -P[:, 2]
    zb = np.full((H, W), -np.inf)
    for f in F:
        x = X[f]; y = Y[f]; z = Z[f]
        xmn = int(max(0, np.floor(x.min()))); xmx = int(min(W - 1, np.ceil(x.max())))
        ymn = int(max(0, np.floor(y.min()))); ymx = int(min(H - 1, np.ceil(y.max())))
        if xmn > xmx or ymn > ymx: continue
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(xmn, xmx + 1) + .5, np.arange(ymn, ymx + 1) + .5)
        a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        c = 1 - a - b
        m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not m.any(): continue
        zz = a * z[0] + b * z[1] + c * z[2]
        sub = zb[ymn:ymx + 1, xmn:xmx + 1]; up = m & (zz > sub); sub[up] = zz[up]
    return zb, s


def jacket_parts(parts):
    body = [v for (m, n), v in parts.items() if m == 'Jacket' and n == 'Jacket_Wool']
    lap = [v for (m, n), v in parts.items() if m == 'Jacket' and n.startswith('Jacket_Lapel')]
    if not body: sys.exit('No Jacket / Jacket_Wool part found')
    return body, lap


def holes(parts):
    body, lap = jacket_parts(parts)
    P, F = merge(body + lap)
    out = {}; tg = np.array([0, 1.42, 0])
    for d in DIRS:
        dv = np.array([float(v) for v in d.split(',')]); dv /= np.linalg.norm(dv)
        up = np.array([0, 1, 0.]); up = up - dv * (up @ dv); up /= np.linalg.norm(up); right = np.cross(up, dv)
        Q = np.c_[-(P - tg) @ right, (P - tg) @ up, -(P - tg) @ dv]
        z, _ = depthmap(Q, F, (-0.18, 0.18, -0.06, 0.06), 1440, 480)
        emp = ~np.isfinite(z); n = 0
        for c in range(emp.shape[1]):
            f = np.where(~emp[:, c])[0]
            if len(f): n += int(emp[f.min():f.max(), c].sum())
        out['holes_' + d.replace(',', '_')] = n
    out['holes_total'] = sum(out.values())
    return out


def shirt_poke(parts):
    sh = [v for (m, n), v in parts.items() if m == 'Shirt']
    if not sh: return {}
    body, lap = jacket_parts(parts)
    PJ, FJ = merge(body)
    FJb = FJ[PJ[FJ][:, :, 1].min(1) > 1.30]
    items = [(PJ, FJb)] + [(p, f) for p, f in lap]
    PJ2, FJ2 = merge(items)
    PS, FS = sh[0]; FS = FS[PS[FS][:, :, 1].min(1) > 1.30]
    x0, x1, z0, z1 = -0.19, 0.19, -0.12, 0.09; S = 2000; W = int((x1 - x0) * S); H = int((z1 - z0) * S)
    T = lambda P_: P_[:, [0, 2, 1]] * [-1, 1, -1]
    Hj, hs = depthmap(T(PJ2), FJ2, (x0, x1, z0, z1), W, H)
    Hs, _ = depthmap(T(PS), FS, (x0, x1, z0, z1), W, H)
    with np.errstate(invalid='ignore'):
        ex = np.where(np.isfinite(Hs) & np.isfinite(Hj), Hs - Hj, np.nan)
    rr, cc = np.mgrid[0:H, 0:W]; X = x0 + (cc + .5) / hs; Z = z1 - (rr + .5) / hs; R = np.hypot(X, Z + 0.005)
    with np.errstate(invalid='ignore'):
        poke = (ex > 0.001) & (R > 0.085)
    return {'shirt_poke_mm2': round(float(poke.sum()) * (1000 / hs) ** 2, 1)}


def validator(path):
    js = os.path.join(ROOT, 'tools', 'validate.js')
    if not os.path.exists(js): return {}
    try:
        r = subprocess.run(['node', js, os.path.abspath(path)], capture_output=True, text=True, timeout=300, cwd=os.path.join(ROOT, 'tools'))
    except Exception:
        return {}
    txt = (r.stdout or '') + (r.stderr or '')
    m = re.search(r'errors\s+(\d+)', txt)
    return {'validator_errors': int(m.group(1))} if m else {}


def run(path):
    parts = load(path); res = {}
    res.update(validator(path)); res.update(holes(parts)); res.update(shirt_poke(parts))
    return res


def verdict(new, old):
    if new == 0: return 'Clean'
    if old is None: return ''
    return 'Fixed' if new < old else ('Made worse' if new > old else 'Same')


def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    newp = sys.argv[1]; prevp = sys.argv[2] if len(sys.argv) > 2 else None
    new = run(newp); old = run(prevp) if prevp else {}
    print(f'\nNEW:      {os.path.basename(newp)}')
    if prevp: print(f'PREVIOUS: {os.path.basename(prevp)}')
    print(f'\n{"check":<22}{"new":>9}' + (f'{"previous":>10}  result' if prevp else ''))
    for k, v in new.items():
        o = old.get(k)
        print(f'{k:<22}{v:>9}' + (f'{o if o is not None else "-":>10}  {verdict(v, o)}' if prevp else f'  {verdict(v, None)}'))
    print('\nA low count is necessary, not sufficient: still look at the close-up and high views.')
    if '--json' in sys.argv: print(json.dumps({'new': new, 'previous': old}))


if __name__ == '__main__':
    main()
