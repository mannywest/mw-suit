"""Surface roughness check (lumps, dents, crumples): how far each cloth vertex sits off the average of its neighbours, along its own normal.
Reported in mm per area, with locations. Lower is better.  Used by full_check.py; also: python3 scripts/bumps.py A.glb [B.glb]"""
import sys, os
import numpy as np
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
THRESH = 0.0025


def bump_clusters(prims, mats=('Jacket_Wool',)):
    import full_check as fc
    out = []
    for pr in prims:
        if pr['mat'] not in mats: continue
        P, F = pr['P'], pr['F']
        key = np.round(P / 1e-4).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
        Pw = P[first]; Fw = inv[F]; n = len(Pw)
        fn, a = fc.tri_normals(Pw, Fw); vn = np.zeros((n, 3))
        for k in range(3): np.add.at(vn, Fw[:, k], fn * a[:, None])
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
        E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]); E = np.vstack([E, E[:, ::-1]])
        A = coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n)).tocsr(); A.data[:] = 1
        deg = np.asarray(A.sum(1)).ravel(); mean = (A @ Pw) / np.maximum(deg, 1)[:, None]
        res = np.abs(((Pw - mean) * vn).sum(1)); res[deg < 3] = 0
        bd = np.bincount(np.concatenate([Fw[:, 0], Fw[:, 1], Fw[:, 2]]), minlength=n) < 3     # skip open-edge vertices (edges are reported elsewhere)
        res[bd] = 0
        out.append((Pw, res))
    if not out: return np.zeros((0, 3)), np.zeros(0)
    return np.vstack([o[0] for o in out]), np.concatenate([o[1] for o in out])


def bumps(prims):
    import full_check as fc
    Pw, res = bump_clusters(prims); bad = res > THRESH; res_d = {}
    z = fc.zone_of(Pw)
    for zn in fc.ZONES: res_d['bumps_' + zn] = int((bad & (z == zn)).sum())
    res_d['bumps_total'] = int(bad.sum()); res_d['bump_max_mm'] = round(float(res.max() * 1000), 1) if len(res) else 0
    cl = []
    if bad.any():
        pos = Pw[bad]; r = res[bad]; used = np.zeros(len(pos), bool); tree = cKDTree(pos)
        for i in np.argsort(-r):
            if used[i]: continue
            idx = [j for j in tree.query_ball_point(pos[i], 0.035) if not used[j]]; used[idx] = True
            cl.append((float(r[idx].sum() * 1000), len(idx), float(r[idx].max() * 1000), pos[i]))
    return res_d, sorted(cl, key=lambda c: -c[0])


if __name__ == '__main__':
    import full_check as fc
    for p in sys.argv[1:]:
        d, cl = bumps(fc.load_full(p)); print(os.path.basename(p), {k: v for k, v in d.items() if v})
        for s, n, mx, pos in cl[:8]: print('   score %5.0f | %3d verts | max %.1f mm | (%+.3f,%.3f,%+.3f)' % (s, n, mx, *pos))
