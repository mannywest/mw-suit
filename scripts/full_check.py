#!/usr/bin/env python3
"""
Whole-jacket check for the MW Tailleur suit GLB.   (measures only: it NEVER edits a model)

    python3 scripts/full_check.py NEW.glb [PREVIOUS.glb] [--sheet out.png]

Why it exists: scripts/check_all.py only looks at the neck. Pockets, front edge, sides etc. were never measured.
This script covers the whole garment and reports results BY AREA, new vs previous, as Fixed / Same / Made worse.
It does not use "done" wording. Lower is better for every number.

Checks
  seethru_*     see-through patches: ortho renders from 12 angles; a patch = a pixel whose nearest cloth is a back
                face (the inside of the cloth shows from outside). Reported in mm2 per area.
  open_*        length (mm) of open (boundary) edges per area. Hem, cuffs and the front opening are expected;
                compare against the previous file.
  nonmanifold   edges shared by more than 2 triangles       dup_tris   duplicate triangles
  slivers       needle/tiny triangles                       shards     small loose pieces (<200 tris)
  spikes        vertices standing off their neighbours (>6 mm): flaps, spikes
  creases       sharp folds (>75 deg) between neighbouring triangles, per area; zigzag = sharp turns along open edges
  inside_out    triangles whose face direction disagrees with the stored shading normal
  shirt_poke    shirt showing above the jacket at the collar (mm2)
  sym_*         left/right mirror mismatch of the jacket body
  uv_*          badly stretched weave coordinates (TEXCOORD_1), missing UV sets
  validator     glTF validator errors
Areas are approximate boxes (neck, shoulder, front_chest, waist_pockets, hem, sleeve, back) so a number can be located.
"""
import sys, os, json
import numpy as np
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try:
    from pygltflib import GLTF2
    from scipy import ndimage as ndi
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
except ImportError:
    sys.exit('Needs: pip install pygltflib numpy scipy')
import check_all as ca

CLOTH = ('Jacket_Wool', 'Jacket_Lapel', 'Jacket_Lapel_Peak', 'Jacket_Lapel_Shawl', 'Waistcoat_Wool', 'Trousers_Wool')
OCCLUDERS_SKIP = ('Buttons', 'Trim')
ZONES = ['neck', 'shoulder', 'front_chest', 'waist_pockets', 'hem', 'sleeve', 'back', 'other']


def zone_of(p):
    """p: (n,3) metres. Approximate area boxes for the jacket (y up, z>0 front)."""
    x, y, z = np.abs(p[:, 0]), p[:, 1], p[:, 2]
    out = np.full(len(p), 'other', dtype=object)
    body = (x < 0.19) & (y >= 0.78)
    out[body & (z <= -0.03)] = 'back'
    out[body & (z > -0.03) & (y < 1.05)] = 'waist_pockets'      # front and sides of the lower jacket incl. pockets
    out[body & (z > -0.03) & (y >= 1.05) & (y < 1.38)] = 'front_chest'
    out[(x >= 0.19) & (y < 1.30)] = 'sleeve'
    out[y < 0.78] = 'hem'                                       # jacket hem is at y 0.707
    out[(y >= 1.28) & (x >= 0.10) & (x < 0.26)] = 'shoulder'
    out[(y >= 1.38) & (x < 0.16)] = 'neck'
    return out


def load_full(path):
    g = GLTF2().load(path); blob = g.binary_blob(); prims = []
    if any('EXT_meshopt' in (e or '') for e in (g.extensionsUsed or [])):
        sys.exit(os.path.basename(path) + ': meshopt-compressed; use the repair GLBs in the repo root')
    for m in g.meshes:
        for p in m.primitives:
            mat = g.materials[p.material].name if p.material is not None else ''
            A = p.attributes
            P = ca._read(g, blob, A.POSITION, 3, '<f4').astype(float)
            F = ca._read(g, blob, p.indices, 1, ca.DTYPE[g.accessors[p.indices].componentType]).reshape(-1, 3).astype(int)
            N = ca._read(g, blob, A.NORMAL, 3, '<f4').astype(float) if A.NORMAL is not None else None
            U0 = ca._read(g, blob, A.TEXCOORD_0, 2, '<f4').astype(float) if A.TEXCOORD_0 is not None else None
            U1 = ca._read(g, blob, A.TEXCOORD_1, 2, '<f4').astype(float) if A.TEXCOORD_1 is not None else None
            prims.append(dict(mesh=m.name, mat=mat, P=P, F=F, N=N, U0=U0, U1=U1))
    return prims


def tri_normals(P, F):
    n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]); l = np.linalg.norm(n, axis=1)
    return n / np.maximum(l[:, None], 1e-15), l / 2


# ---------------------------------------------------------------- see-through
VIEWS = [(az, 10) for az in range(0, 360, 45)] + [(az, 35) for az in (0, 90, 180, 270)]


def rasterise(P, F, tid, right, up, dv, s, box):
    x0, x1, y0, y1 = box; W = int((x1 - x0) * s) + 1; H = int((y1 - y0) * s) + 1
    X = (P @ right - x0) * s; Y = (y1 - P @ up) * s; Z = P @ dv
    zb = np.full((H, W), -np.inf); ib = np.full((H, W), -1, dtype=np.int64)
    for k in range(len(F)):
        f = F[k]; x = X[f]; y = Y[f]; z = Z[f]
        xmn = int(max(0, np.floor(x.min()))); xmx = int(min(W - 1, np.ceil(x.max())))
        ymn = int(max(0, np.floor(y.min()))); ymx = int(min(H - 1, np.ceil(y.max())))
        if xmn > xmx or ymn > ymx: continue
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(xmn, xmx + 1) + .5, np.arange(ymn, ymx + 1) + .5)
        a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        c = 1 - a - b; m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not m.any(): continue
        zz = a * z[0] + b * z[1] + c * z[2]
        sz = zb[ymn:ymx + 1, xmn:xmx + 1]; si = ib[ymn:ymx + 1, xmn:xmx + 1]; up_ = m & (zz > sz)
        sz[up_] = zz[up_]; si[up_] = tid[k]
    return zb, ib, X, Y


def see_through(prims, want_sheet=False):
    P_all, F_all, cloth_tri, owner = [], [], [], []; off = 0; N_all = []
    for pr in prims:
        if pr['mat'] in OCCLUDERS_SKIP: continue
        P_all.append(pr['P']); F_all.append(pr['F'] + off)
        cloth_tri.append(np.full(len(pr['F']), pr['mat'] in CLOTH or pr['mat'] == 'Jacket_Lining')); owner += [pr['mat']] * len(pr['F']); off += len(pr['P'])
    P = np.vstack(P_all); F = np.vstack(F_all); is_cloth = np.concatenate(cloth_tri); owner = np.array(owner, dtype=object)
    Nt, At = tri_normals(P, F); ok = At > 1e-9
    F = F[ok]; Nt = Nt[ok]; is_cloth = is_cloth[ok]; owner = owner[ok]
    s = 800.0  # pixels per metre (0.8 px per mm)
    lo = P.min(0); hi = P.max(0); c0 = (lo + hi) / 2; R = np.linalg.norm(hi - lo) / 2 + 0.02
    patches = []; masks = {}
    for az, el in VIEWS:
        a, e = np.radians(az), np.radians(el)
        dv = np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)]); dv /= np.linalg.norm(dv)
        right = np.cross([0, 1, 0], dv); right /= np.linalg.norm(right); up = np.cross(dv, right)
        Pc = P - c0
        # only keep triangles facing either way (we need back faces too); render all
        proj_x = Pc @ right; proj_y = Pc @ up
        box = (proj_x.min() - 0.005, proj_x.max() + 0.005, proj_y.min() - 0.005, proj_y.max() + 0.005)
        zb, ib, X, Y = rasterise(Pc, F, np.arange(len(F)), right, up, dv, s, box)
        vis = ib >= 0; t = np.where(vis, ib, 0)
        front = (Nt[t] @ dv) > 0  # (H,W) via per-pixel gather
        front = np.einsum('ijk,k->ij', Nt[t], dv) > 0
        mask = vis & is_cloth[t] & ((~front) | (owner[t] == 'Jacket_Lining'))   # a back face, or the lining layer, nearest to the camera = we are looking into the garment
        mask = ndi.binary_opening(mask, structure=np.ones((2, 2))) if mask.any() else mask
        lab, n = ndi.label(ndi.binary_dilation(mask, iterations=1) & vis)
        masks[(az, el)] = (mask, vis)
        for k in range(1, n + 1):
            comp = (lab == k) & mask; px = int(comp.sum())
            if px < 4: continue
            ys, xs = np.nonzero(comp); cy, cx = ys.mean(), xs.mean(); zc = zb[int(round(cy)), int(round(cx))]
            if not np.isfinite(zc):                    # centre pixel empty: use the nearest pixel of the patch itself
                k_ = int(np.argmin((ys - cy) ** 2 + (xs - cx) ** 2)); cy, cx = float(ys[k_]), float(xs[k_]); zc = zb[ys[k_], xs[k_]]
            x_m = box[0] + cx / s; y_m = box[3] - cy / s
            world = c0 + right * x_m + up * y_m + dv * zc
            mat = owner[ib[int(round(cy)), int(round(cx))]]
            patches.append(dict(view=(az, el), mm2=px / (s / 1000) ** 2, pos=world, mat=mat))
    # cluster patches across views (same place seen from several angles)
    clusters = []
    if patches:
        pos = np.array([p['pos'] for p in patches]); used = np.zeros(len(patches), bool); tree = cKDTree(pos)
        for i in np.argsort([-p['mm2'] for p in patches]):
            if used[i]: continue
            idx = [j for j in tree.query_ball_point(pos[i], 0.035) if not used[j]]
            used[idx] = True
            clusters.append(dict(mm2=max(patches[j]['mm2'] for j in idx), views=len({patches[j]['view'] for j in idx}), pos=pos[i], mat=patches[i]['mat']))
    return clusters, masks


# ---------------------------------------------------------------- topology / shape
def weld(P, F):
    key = np.round(P * 1e4).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel(); return P[first], inv[F]


def topology(prims):
    jk = [pr for pr in prims if pr['mesh'] == 'Jacket' and pr['mat'] in CLOTH[:4]]
    res = {}
    if not jk: return res
    P0 = jk[0]['P']; Fs = [pr['F'] for pr in jk]; F = np.vstack(Fs)
    Pw, W = weld(P0, F)
    # degenerate after welding
    W = W[(W[:, 0] != W[:, 1]) & (W[:, 1] != W[:, 2]) & (W[:, 0] != W[:, 2])]
    srt = np.sort(W, axis=1); res['dup_tris'] = int(len(srt) - len(np.unique(srt, axis=0)))
    Nt, At = tri_normals(Pw, W)
    # slivers
    e = np.stack([np.linalg.norm(Pw[W[:, 0]] - Pw[W[:, 1]], axis=1), np.linalg.norm(Pw[W[:, 1]] - Pw[W[:, 2]], axis=1), np.linalg.norm(Pw[W[:, 2]] - Pw[W[:, 0]], axis=1)], 1)
    alt = 2 * At / np.maximum(e.max(1), 1e-12)
    res['slivers'] = int(((alt < 0.0002) | (At < 3e-8)).sum())
    # edges
    E = defaultdict(list)
    for ti, t in enumerate(W):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): E[(min(a, b), max(a, b))].append(ti)
    openE = [k for k, v in E.items() if len(v) == 1]; nm = [k for k, v in E.items() if len(v) > 2]
    res['nonmanifold'] = len(nm)
    zones = {z: 0.0 for z in ZONES}
    if openE:
        a = np.array([k[0] for k in openE]); b = np.array([k[1] for k in openE]); mid = (Pw[a] + Pw[b]) / 2; ln = np.linalg.norm(Pw[a] - Pw[b], axis=1)
        zz = zone_of(mid)
        for z in ZONES: zones[z] = float(ln[zz == z].sum() * 1000)
    for z in ZONES: res['open_' + z + '_mm'] = round(zones[z])
    # zigzag: sharp turns along boundary vertices with exactly 2 boundary edges
    nb = defaultdict(list)
    for a, b in openE: nb[a].append(b); nb[b].append(a)
    zig = defaultdict(int)
    for v, nbs in nb.items():
        if len(nbs) != 2: continue
        d1 = Pw[nbs[0]] - Pw[v]; d2 = Pw[nbs[1]] - Pw[v]; c = d1 @ d2 / max(np.linalg.norm(d1) * np.linalg.norm(d2), 1e-12)
        if c > 0.0: zig[zone_of(Pw[v][None])[0]] += 1  # turn sharper than 90 deg
    for z in ZONES: res['zigzag_' + z] = zig[z]
    # creases on interior edges
    cr = defaultdict(int)
    for k, v in E.items():
        if len(v) != 2: continue
        if Nt[v[0]] @ Nt[v[1]] < np.cos(np.radians(75)): cr[zone_of(((Pw[k[0]] + Pw[k[1]]) / 2)[None])[0]] += 1
    for z in ZONES: res['creases_' + z] = cr[z]
    # spikes: interior vertices far from their neighbour mean
    nbr = defaultdict(set); bnd = set(x for k in openE + nm for x in k)
    for a, b in E: nbr[a].add(b); nbr[b].add(a)
    sp = defaultdict(int)
    for v, ns in nbr.items():
        if v in bnd or len(ns) < 3: continue
        if np.linalg.norm(Pw[v] - Pw[list(ns)].mean(0)) > 0.006: sp[zone_of(Pw[v][None])[0]] += 1
    res['spikes'] = int(sum(sp.values()))
    # shards: small connected components
    n = len(Pw); r = np.concatenate([W[:, 0], W[:, 1]]); c = np.concatenate([W[:, 1], W[:, 2]])
    nc, lab = connected_components(coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n)), directed=False)
    tri_lab = lab[W[:, 0]]; cnt = np.bincount(tri_lab, minlength=nc); small = np.where((cnt > 0) & (cnt < 200))[0]
    res['shards'] = int(len(small)); res['shard_tris'] = int(cnt[small].sum())
    # symmetry of body vertices
    body = np.unique(W.ravel()); B = Pw[body]; tree = cKDTree(B); d, _ = tree.query(B * [-1, 1, 1])
    res['sym_p90_mm'] = round(float(np.percentile(d, 90) * 1000), 1); res['sym_over10mm_pct'] = round(float((d > 0.01).mean() * 100), 1)
    # inside-out vs stored normal
    bad = 0
    for pr in jk:
        if pr['N'] is None: continue
        fn, _ = tri_normals(pr['P'], pr['F']); vn = pr['N'][pr['F']].mean(1); bad += int(((fn * vn).sum(1) < -0.05).sum())
    res['inside_out'] = bad
    # UV
    stretch = 0; miss = 0
    for pr in jk:
        if pr['U0'] is None or pr['U1'] is None: miss += 1
        U = pr['U1']
        if U is None: continue
        F_ = pr['F']; A3 = tri_normals(pr['P'], F_)[1]; u = U[F_]; A2 = 0.5 * ((u[:, 1, 0] - u[:, 0, 0]) * (u[:, 2, 1] - u[:, 0, 1]) - (u[:, 2, 0] - u[:, 0, 0]) * (u[:, 1, 1] - u[:, 0, 1]))
        okk = A3 > 1e-9
        ratio = np.abs(A2[okk]) / A3[okk]; med = np.median(ratio[ratio > 0]) if (ratio > 0).any() else 1
        stretch += int(((ratio > med * 2.5) | (ratio < med / 2.5)).sum())
    res['uv_stretch_outliers'] = stretch; res['uv_missing_sets'] = miss
    return res


def run(path, sheet=None):
    prims = load_full(path); res = {}
    res.update(ca.validator(path))
    cl, masks = see_through(prims)
    tot = 0.0; per = {z: 0.0 for z in ZONES}; cnt = {z: 0 for z in ZONES}
    for c in cl:
        z = zone_of(c['pos'][None])[0] if c['mat'] in CLOTH[:4] else ('waistcoat' if c['mat'].startswith('Waist') else 'trousers')
        per[z] = per.get(z, 0) + c['mm2']; cnt[z] = cnt.get(z, 0) + 1; tot += c['mm2']
    res['seethru_total_mm2'] = round(tot)
    for z in list(per): res['seethru_' + z + '_mm2'] = round(per[z])
    res.update(topology(prims))
    import bumps as _b; _bd, _bc = _b.bumps(prims); res.update(_bd); res['_bump_clusters'] = _bc[:6]
    parts = ca.load(path); res.update(ca.holes(parts)); res.update(ca.shirt_poke(parts))
    return res, cl, masks


def verdict(new, old):
    if old is None: return ''
    if new == old: return 'Same'
    tol = max(1.0, 0.03 * abs(old))
    if abs(new - old) <= tol: return 'Same'
    return 'Fixed' if new < old else 'Made worse'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    sheet = sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None
    if sheet and sheet in args: args.remove(sheet)
    if not args: sys.exit(__doc__)
    newp = args[0]; prevp = args[1] if len(args) > 1 else None
    new, cl, masks = run(newp); old = run(prevp)[0] if prevp else {}
    print(f'\nNEW:      {os.path.basename(newp)}' + (f'\nPREVIOUS: {os.path.basename(prevp)}' if prevp else ''))
    print(f'\n{"check":<26}{"new":>9}' + (f'{"previous":>10}  result' if prevp else ''))
    for k, v in new.items():
        if k.startswith('_'): continue
        if k.startswith('holes_') and k != 'holes_total': continue
        if v == 0 and old.get(k, 0) == 0 and (k.startswith(('open_', 'creases_', 'zigzag_', 'seethru_')) and k != 'seethru_total_mm2'): continue
        o = old.get(k)
        print(f'{k:<26}{v:>9}' + (f'{o if o is not None else "-":>10}  {verdict(v, o)}' if prevp else ''))
    print('\nBumpiest spots (new file): score | verts | max mm off neighbours | where')
    for sc, nv, mx, ps in new.get('_bump_clusters', [])[:5]: print('  %6.0f | %3d | %4.1f | (%+.3f,%.3f,%+.3f)' % (sc, nv, mx, *ps))
    print('\nBiggest see-through patches (new file): mm2 | seen from n of 12 views | where (x,y,z in metres) | cloth')
    for c in sorted(cl, key=lambda c: -c['mm2'])[:8]:
        print(f"  {c['mm2']:7.0f} | {c['views']:2d} | ({c['pos'][0]:+.3f},{c['pos'][1]:.3f},{c['pos'][2]:+.3f}) | {c['mat']}")
    print('''
NOT CHECKED (needs your eyes): how crumpled or lumpy a fold LOOKS, lapel shape vs your reference photo, flat "ears"
over the shoulders, colour/texture realism, buttons and trim placement, and how it looks in the website builder.
Expected non-zero: hem, cuffs and the front opening always show some open edge / inside face; compare to the previous file.''')
    if sheet:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, axs = plt.subplots(2, 6, figsize=(15, 6.5), dpi=80)
        for ax, ((az, el), (mask, vis)) in zip(axs.ravel(), masks.items()):
            im = np.zeros(vis.shape + (3,), np.uint8); im[vis] = (70, 75, 90); im[mask] = (255, 0, 255)
            ax.imshow(im); ax.set_title(f'az {az} el {el}', fontsize=8); ax.axis('off')
        plt.tight_layout(); plt.savefig(sheet); print('sheet saved:', sheet)
    if '--json' in sys.argv: print(json.dumps({'new': new, 'previous': old}))


if __name__ == '__main__':
    main()
