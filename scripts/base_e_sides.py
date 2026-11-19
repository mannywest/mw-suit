#!/usr/bin/env python3
"""Base repair step E: close see-through holes in the jacket body (Jacket_Wool) with new cloth.
    python3 scripts/base_e_sides.py IN.glb OUT.glb [zones=waist_pockets,hem] [passes=2]
Method: for every see-through patch (inside of the cloth showing from outside, same test as full_check.py) the missing
outer surface is rebuilt from the cloth around it (smooth depth fill between the surrounding edges), meshed as a grid,
run ~6 mm under the existing cloth around the hole so there is no crack, and added to Jacket_Wool.
Weave coordinates are copied from the nearest existing cloth. IN.glb is never modified."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
import full_check as fc
from common import load
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from pygltflib import Accessor, BufferView

WHERE = None; MIN_MM2 = 60.0; STRIDE = 3; PAD = 6; SINK = 0.0008; S = 800.0


def harmonic(depth, known, unknown, iters=600):
    d = np.where(known, depth, 0.0); d[unknown] = np.median(depth[known])
    use = known | unknown
    for _ in range(iters):
        acc = np.zeros_like(d); w = np.zeros_like(d)
        for sh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(d * use, sh, (0, 1)); w += np.roll(use.astype(float), sh, (0, 1))
        nd = acc / np.maximum(w, 1)
        d[unknown] = nd[unknown]
    return d


def fills_for(path, zones):
    prims = fc.load_full(path); Ps, Fs, cl = [], [], []; off = 0
    for pr in prims:
        if pr['mat'] in fc.OCCLUDERS_SKIP: continue
        Ps.append(pr['P']); Fs.append(pr['F'] + off); cl.append(np.full(len(pr['F']), pr['mat'] in fc.CLOTH)); off += len(pr['P'])
    P = np.vstack(Ps); F = np.vstack(Fs); is_cloth = np.concatenate(cl)
    Nt, At = fc.tri_normals(P, F); ok = At > 1e-9; F = F[ok]; Nt = Nt[ok]; is_cloth = is_cloth[ok]
    lo, hi = P.min(0), P.max(0); c0 = (lo + hi) / 2
    out = []; done = []
    for az, el in fc.VIEWS:
        a, e = np.radians(az), np.radians(el)
        dv = np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)]); dv /= np.linalg.norm(dv)
        right = np.cross([0, 1, 0], dv); right /= np.linalg.norm(right); up = np.cross(dv, right)
        Pc = P - c0; px, py = Pc @ right, Pc @ up
        box = (px.min() - .005, px.max() + .005, py.min() - .005, py.max() + .005)
        zb, ib, X, Y = fc.rasterise(Pc, F, np.arange(len(F)), right, up, dv, S, box)
        vis = ib >= 0; t = np.where(vis, ib, 0)
        front = np.einsum('ijk,k->ij', Nt[t], dv) > 0
        mask = vis & is_cloth[t] & (~front); mask = ndi.binary_opening(mask, structure=np.ones((2, 2)))
        lab, n = ndi.label(ndi.binary_dilation(mask, iterations=1) & vis)
        objs = ndi.find_objects(lab)
        for k in range(1, n + 1):
            comp = (lab == k) & mask; mm2 = comp.sum() / (S / 1000) ** 2
            if mm2 < MIN_MM2: continue
            ys, xs = np.nonzero(comp); cy, cx = int(ys.mean()), int(xs.mean())
            wpos = c0 + right * (box[0] + cx / S) + up * (box[3] - cy / S) + dv * zb[cy, cx]
            if fc.zone_of(wpos[None])[0] not in zones: continue
            if WHERE is not None and not WHERE(wpos): continue
            if any(np.linalg.norm(wpos - q) < 0.03 for q in done): continue
            r0, r1 = max(0, ys.min() - 20), min(mask.shape[0], ys.max() + 21); c_0, c_1 = max(0, xs.min() - 20), min(mask.shape[1], xs.max() + 21)
            sl = (slice(r0, r1), slice(c_0, c_1))
            H = ndi.binary_dilation(comp, iterations=2)[sl]
            ring = ndi.binary_dilation(H, iterations=PAD + 3) & ~H
            Kc = vis[sl] & front[sl] & is_cloth[t][sl] & ring
            if Kc.sum() < 20: continue
            zz = zb[sl]; med = np.median(zz[Kc]); Kc &= np.abs(zz - med) < 0.03
            if Kc.sum() < 20: continue
            dep = harmonic(zz, Kc, H)
            D = ndi.binary_dilation(H, iterations=PAD) & (Kc | H)
            gi, gj = np.mgrid[0:H.shape[0]:STRIDE, 0:H.shape[1]:STRIDE]
            valid = D[gi, gj]; idx = -np.ones(valid.shape, int); idx[valid] = np.arange(valid.sum())
            V = []
            for ii, jj in zip(gi[valid], gj[valid]):
                row = ii + r0; col = jj + c_0
                V.append(c0 + right * (box[0] + (col + .5) / S) + up * (box[3] - (row + .5) / S) + dv * (dep[ii, jj] - SINK))
            V = np.array(V); T = []
            for a_ in range(valid.shape[0] - 1):
                for b_ in range(valid.shape[1] - 1):
                    q = (idx[a_, b_], idx[a_ + 1, b_], idx[a_ + 1, b_ + 1], idx[a_, b_ + 1])
                    if min(q) < 0: continue
                    T += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
            if not T: continue
            T = np.array(T); used = np.unique(T); remap = -np.ones(len(V), int); remap[used] = np.arange(len(used)); V = V[used]; T = remap[T]; nn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
            flip = (nn @ dv) < 0; T[flip] = T[flip][:, [0, 2, 1]]
            out.append(dict(V=V, T=T, dv=dv, mm2=mm2, pos=wpos)); done.append(wpos)
            print('  fill %-5s %5.0f mm2 at (%+.3f,%.3f,%+.3f) view az%d: %d verts %d tris' % (fc.zone_of(wpos[None])[0], mm2, *wpos, az, len(V), len(T)))
    return out


def write(src, dst, fills, drop=None):
    g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
    ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; Fb = Fs[ib]
    if drop is not None: Fb = Fb[~drop]
    ub = np.unique(Fb.ravel())
    from scipy.sparse import coo_matrix; from scipy.sparse.csgraph import connected_components
    _e = np.vstack([Fb[:, [0, 1]], Fb[:, [1, 2]]]); _m = coo_matrix((np.ones(len(_e)), (_e[:, 0], _e[:, 1])), shape=(len(P), len(P)))
    isl = connected_components(_m, directed=False)[1]
    def _dens(UU):
        t = P[Fb]; A3 = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / 2; u = UU[Fb]
        A2 = 0.5 * np.abs((u[:, 1, 0] - u[:, 0, 0]) * (u[:, 2, 1] - u[:, 0, 1]) - (u[:, 2, 0] - u[:, 0, 0]) * (u[:, 1, 1] - u[:, 0, 1])); r = A2[A3 > 1e-9] / A3[A3 > 1e-9]
        return float(np.sqrt(np.median(r[r > 0])))
    dens0, dens1 = _dens(U0), _dens(U1); print('uv density', dens0, dens1)
    tree = cKDTree(P[ub]); newP, newN, newU0, newU1, newT = [], [], [], [], []; base = len(P)
    for f in fills:
        V, T = f['V'], f['T']; fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]); vn = np.zeros_like(V)
        for k in range(3): np.add.at(vn, T[:, k], fn)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
        d, j = tree.query(V, k=3); w = 1 / np.maximum(d, 1e-5); w /= w.sum(1, keepdims=True)
        u0 = (U0[ub][j] * w[:, :, None]).sum(1); u1 = (U1[ub][j] * w[:, :, None]).sum(1)
        c = V.mean(0); R = np.linalg.norm(V - c, axis=1).max() + 0.03; near = ub[np.linalg.norm(P[ub] - c, axis=1) < R]
        near = near[(N[near] @ vn.mean(0)) > 0.5]
        if len(near):                                         # use ONE weave island only (the biggest nearby) and fit a smooth local map
            cnt = np.bincount(isl[near]); k = cnt.argmax(); cand = near[isl[near] == k]
            if len(cand) > 40: cand = cand[np.argsort(np.linalg.norm(P[cand] - c, axis=1))[:40]]
            if len(cand) >= 8:
                A = np.c_[P[cand], np.ones(len(cand))]; sols = [np.linalg.lstsq(A, UU[cand], rcond=None)[0] for UU in (U0, U1)]
                rms = max(np.sqrt(((A @ sol - UU[cand]) ** 2).mean()) for sol, UU in zip(sols, (U0, U1)))
                B = np.c_[V, np.ones(len(V))]; u0n, u1n = B @ sols[0], B @ sols[1]
                print('   uv: island fit %d refs rms %.4f' % (len(cand), rms))
                if rms < 0.05:
                    # sheet-local, evenly scaled weave: keeps the weave size/orientation of the cloth around it, with no streaking on sideways sheets
                    Vc = V - c; _, _, vt = np.linalg.svd(Vc, full_matrices=False); t1, t2 = vt[0], vt[1]; loc = np.c_[Vc @ t1, Vc @ t2]; res_ = []
                    for sol, UU, dens in ((sols[0], U0, dens0), (sols[1], U1, dens1)):
                        Jp = sol[:3].T @ np.c_[t1, t2]; Uu, _, Vt = np.linalg.svd(Jp); Rot = Uu @ Vt
                        uvc = np.r_[c, 1] @ sol; res_.append(uvc + dens * (loc @ Rot.T))
                    u0, u1 = res_
        newT.append(T + base); newP.append(V); newN.append(vn); newU0.append(u0); newU1.append(u1); base += len(V)
    if not newP and drop is None: print('nothing to add'); return 0
    if not newP: newP, newN, newU0, newU1 = [np.zeros((0, 3))], [np.zeros((0, 3))], [np.zeros((0, 2))], [np.zeros((0, 2))]
    PP = np.vstack([P] + newP); NN = np.vstack([N] + newN); UU0 = np.vstack([U0] + newU0); UU1 = np.vstack([U1] + newU1)
    Fb2 = np.vstack([Fb] + newT); bl = bytearray(blob)
    def addacc(data, typ, ctype, target, mn=None, mx=None):
        while len(bl) % 4: bl.append(0)
        off = len(bl); bl.extend(data.tobytes())
        g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
        g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
        return len(g.accessors) - 1
    p32 = PP.astype('<f4')
    ids = [addacc(p32, 'VEC3', 5126, 34962, p32.min(0).tolist(), p32.max(0).tolist()), addacc(NN.astype('<f4'), 'VEC3', 5126, 34962),
           addacc(UU0.astype('<f4'), 'VEC2', 5126, 34962), addacc(UU1.astype('<f4'), 'VEC2', 5126, 34962)]
    for p in pr: p.attributes.POSITION, p.attributes.NORMAL, p.attributes.TEXCOORD_0, p.attributes.TEXCOORD_1 = ids
    pr[ib].indices = addacc(Fb2.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
    g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
    return sum(len(x) for x in newT)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    zones = (sys.argv[3] if len(sys.argv) > 3 else 'waist_pockets,hem').split(','); passes = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    cur = src
    for ps in range(passes):
        print('pass', ps + 1, 'zones', zones); fl = fills_for(cur, zones)
        nxt = dst if ps == passes - 1 else '/tmp/stepE_pass%d.glb' % (ps + 1)
        n = write(cur, nxt, fl); print('  added', n, 'triangles ->', nxt)
        if not n:
            if nxt != dst: import shutil; shutil.copy(cur, dst)
            break
        cur = nxt
