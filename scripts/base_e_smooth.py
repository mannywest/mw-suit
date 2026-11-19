#!/usr/bin/env python3
"""Smooth lumps in Jacket_Wool (only vertices the bump check flags, only in the chosen areas; open-edge vertices stay put).
    python3 scripts/base_e_smooth.py IN.glb OUT.glb [zones=waist_pockets,hem,back,sleeve] [thresh_mm=2.5]"""
import sys, os
import numpy as np
from scipy.sparse import coo_matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
import full_check as fc
from common import load
from pygltflib import Accessor, BufferView

src, dst = sys.argv[1], sys.argv[2]
zones = (sys.argv[3] if len(sys.argv) > 3 else 'waist_pockets,hem,back,sleeve').split(','); thr = float(sys.argv[4]) / 1000 if len(sys.argv) > 4 else 0.0025
g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; F = Fs[ib]
key = np.round(P / 1e-4).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
Pw = P[first].copy(); Fw = inv[F]; n = len(Pw)
E = np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]); Es = np.sort(E, 1); u, c = np.unique(Es, axis=0, return_counts=True)
bnd = np.zeros(n, bool); bnd[u[c == 1].ravel()] = True; bnd[u[c > 2].ravel()] = True
E2 = np.vstack([E, E[:, ::-1]]); A = coo_matrix((np.ones(len(E2)), (E2[:, 0], E2[:, 1])), shape=(n, n)).tocsr(); A.data[:] = 1; deg = np.asarray(A.sum(1)).ravel()
used = np.zeros(n, bool); used[Fw.ravel()] = True
def vnormals(Pw):
    fn, a = fc.tri_normals(Pw, Fw); vn = np.zeros((n, 3))
    for k in range(3): np.add.at(vn, Fw[:, k], fn * a[:, None])
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
zone = fc.zone_of(Pw); sel = used & ~bnd & np.isin(zone, zones) & (deg >= 3)
moved = np.zeros(n, bool); before = None
P0 = Pw.copy(); CAP = 0.003
for it in range(10):
    vn = vnormals(Pw); mean = (A @ Pw) / np.maximum(deg, 1)[:, None]; res = ((Pw - mean) * vn).sum(1)
    if before is None: before = int((np.abs(res)[sel] > thr).sum())
    bad = sel & (np.abs(res) > thr * 0.6)
    if not bad.any(): break
    Pw[bad] += (mean[bad] - Pw[bad]) * 0.6; moved |= bad
    d = Pw - P0; L = np.linalg.norm(d, axis=1); k = L > CAP; Pw[k] = P0[k] + d[k] / L[k][:, None] * CAP
vn = vnormals(Pw); P2 = P.copy(); N2 = N.copy(); P2 = Pw[inv]; mv = moved[inv]
nbv = moved[inv]
pass
dmax = np.abs(Pw - P[first]).max() * 1000
print('flagged before %d; vertices moved %d; largest move %.1f mm; iterations %d' % (before, moved.sum(), dmax, it + 1))
P2 = np.where(moved[inv][:, None], P2, P)
bl = bytearray(blob)
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    off = len(bl); bl.extend(data.tobytes())
    g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
    return len(g.accessors) - 1
p32 = P2.astype('<f4'); ip = addacc(p32, 'VEC3', 5126, 34962, p32.min(0).tolist(), p32.max(0).tolist()); inn = addacc(N2.astype('<f4'), 'VEC3', 5126, 34962)
for p in pr: p.attributes.POSITION = ip; p.attributes.NORMAL = inn
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst); print('saved', dst)
