#!/usr/bin/env python3
"""Shawl lapel: replace the sharp tapering tip with a rounded (half-ellipse) end.   python3 scripts/shawl_round_end.py IN.glb OUT.glb [y_tip=1.115] [y_full=1.22]
Each row of the lapel below y_full is narrowed toward the inner (front) edge by k(y)=sqrt(1-((y_full-y)/(y_full-y_tip))^2); topology unchanged."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from pygltflib import Accessor, BufferView
src, dst = sys.argv[1], sys.argv[2]; yt = float(sys.argv[3]) if len(sys.argv) > 3 else 1.115; yf = float(sys.argv[4]) if len(sys.argv) > 4 else 1.22
g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
i = [k for k, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Lapel_Shawl'][0]; F = Fs[i]; v = np.unique(F); P2 = P.copy(); N2 = N.copy()
for sgn in (1, -1):
    m = v[(np.sign(P[v, 0]) == sgn) & (P[v, 1] < yf + 0.03)]; ys = P[m, 1]; xa = np.abs(P[m, 0])
    bins = np.arange(yt - 0.005, yf + 0.03, 0.01); xin = []; yb = []
    for b in bins:
        s = (ys >= b) & (ys < b + 0.01)
        if s.sum() > 3: xin.append(xa[s].min()); yb.append(b + 0.005)
    co = np.polyfit(yb, xin, 1)                                   # inner (front) edge line: x_in(y)
    low = m[(P[m, 1] < yf) & (P[m, 1] >= yt - 0.002)]
    t = np.clip((yf - P[low, 1]) / (yf - yt), 0, 1); k = np.sqrt(np.maximum(0, 1 - t * t))
    xi = np.polyval(co, P[low, 1]); x_new = xi + (np.abs(P[low, 0]) - xi) * k
    P2[low, 0] = sgn * np.maximum(x_new, xi)
    print('side %+d: inner edge x = %.4f + %.3f*(y-1.115) (approx); rows reshaped: %d points; tip width now %.1f mm' % (sgn, np.polyval(co, 1.115), co[0], len(low), (np.abs(P2[low, 0]) - xi)[P[low, 1] < yt + 0.01].max() * 1000))
# recompute normals of moved points from the lapel triangles
mv = np.abs(P2 - P).sum(1) > 0; fn = np.cross(P2[F[:, 1]] - P2[F[:, 0]], P2[F[:, 2]] - P2[F[:, 0]]); vn = np.zeros_like(P)
for k in range(3): np.add.at(vn, F[:, k], fn)
vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12); keep = mv & (np.einsum('ij,ij->i', vn, N) > 0.3); N2[keep] = vn[keep]
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
