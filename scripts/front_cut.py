#!/usr/bin/env python3
"""Cut the jacket body's front edge back to ONE smooth curve around the top button (symmetric left/right).
    python3 scripts/front_cut.py IN.glb OUT.glb
Curve x_e(y) (metres from the centre line): 1.5 mm up to y=1.05, smooth ease to 36 mm at y=1.15, then +0.2 mm per mm of height (follows the old edge).
Cloth with |x| < x_e(y) at the front (z>0.10, 1.00<y<1.32) is removed. Triangles crossing the curve are split exactly (positions, shading normals and both UV sets interpolated)."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from pygltflib import Accessor, BufferView
Y0, Y1, XA, XB = 1.05, 1.15, 0.0015, 0.036
def xe(y):
    t = np.clip((y - Y0) / (Y1 - Y0), 0, 1); s = t * t * (3 - 2 * t)
    return np.where(y <= Y1, XA + (XB - XA) * s, XB + (y - Y1) * 0.2)
def fval(P):
    f = np.abs(P[:, 0]) - xe(P[:, 1]); out = (P[:, 2] < 0.10) | (P[:, 1] < 1.0) | (P[:, 1] > 1.32)
    return np.where(out, 0.05, np.minimum(f, 0.05))
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
    ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; F = Fs[ib]
    f = fval(P); fv = f[F]; neg = (fv < 0).sum(1); keep = F[neg == 0]; cross = np.nonzero((neg == 1) | (neg == 2))[0]
    PP, NN, A0, A1 = [list(P)], [list(N)], [list(U0)], [list(U1)]; nP = len(P); extra = []; newv = {}
    def mk(a, b):                                    # point where the curve crosses edge a-b (cached so neighbouring triangles share it)
        k = (min(a, b), max(a, b))
        if k in newv: return newv[k]
        t = f[a] / (f[a] - f[b]); nonlocal_n = len(PP[0])
        PP[0].append(P[a] + t * (P[b] - P[a])); n_ = N[a] + t * (N[b] - N[a]); NN[0].append(n_ / max(np.linalg.norm(n_), 1e-9))
        A0[0].append(U0[a] + t * (U0[b] - U0[a])); A1[0].append(U1[a] + t * (U1[b] - U1[a])); newv[k] = len(PP[0]) - 1; return newv[k]
    for t in cross:
        a, b, c = F[t]; v = [a, b, c]; fs = [f[a], f[b], f[c]]
        # rotate so that index 0 is the odd vertex out
        sgn = [x < 0 for x in fs]
        if sum(sgn) == 1: o = sgn.index(True)
        else: o = sgn.index(False)
        v = [v[o], v[(o + 1) % 3], v[(o + 2) % 3]]
        m1 = mk(v[0], v[1]); m2 = mk(v[0], v[2])
        if sum(sgn) == 1:                            # one vertex cut away -> keep quad (v1, v2, m2, m1)
            extra += [(v[1], v[2], m2), (v[1], m2, m1)]
        else:                                        # one vertex kept -> keep small triangle (v0, m1, m2)
            extra += [(v[0], m1, m2)]
    Fn = np.vstack([keep, np.array(extra, dtype=int).reshape(-1, 3)])
    PA = np.array(PP[0]); NA = np.array(NN[0]); UA0 = np.array(A0[0]); UA1 = np.array(A1[0])
    print('triangles: %d -> %d (removed %d fully, split %d); new points %d' % (len(F), len(Fn), (neg == 3).sum(), len(cross), len(PA) - nP))
    bl = bytearray(blob)
    def addacc(data, typ, ctype, target, mn=None, mx=None):
        while len(bl) % 4: bl.append(0)
        off = len(bl); bl.extend(data.tobytes())
        g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
        g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
        return len(g.accessors) - 1
    p32 = PA.astype('<f4')
    ids = [addacc(p32, 'VEC3', 5126, 34962, p32.min(0).tolist(), p32.max(0).tolist()), addacc(NA.astype('<f4'), 'VEC3', 5126, 34962), addacc(UA0.astype('<f4'), 'VEC2', 5126, 34962), addacc(UA1.astype('<f4'), 'VEC2', 5126, 34962)]
    for p in pr: p.attributes.POSITION, p.attributes.NORMAL, p.attributes.TEXCOORD_0, p.attributes.TEXCOORD_1 = ids
    pr[ib].indices = addacc(Fn.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
    g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst); print('saved', dst)
