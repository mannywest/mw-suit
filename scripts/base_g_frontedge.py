#!/usr/bin/env python3
"""Base repair step G: straighten the ragged FRONT EDGE of the jacket body (where the lapel attaches).
Each open-edge vertex in the front-edge box is eased toward the average of its two neighbours ALONG the edge (max move 4 mm total).
    python3 scripts/base_g_frontedge.py IN.glb OUT.glb"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from pygltflib import Accessor, BufferView
src, dst = sys.argv[1], sys.argv[2]
g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; F = Fs[ib]
key = np.round(P / 1e-4).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
Pw = P[first].copy(); W = inv[F]; n = len(Pw)
E = np.vstack([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]); Es = np.sort(E, 1); u, c = np.unique(Es, axis=0, return_counts=True); be = u[c == 1]
nb = [[] for _ in range(n)]
for a, b in be: nb[a].append(b); nb[b].append(a)
box = lambda p: (np.abs(p[0]) < 0.16) and (p[1] > 1.0) and (p[2] > 0.08)
sel = np.array([i for i in range(n) if len(nb[i]) == 2 and box(Pw[i])]); P0 = Pw.copy()
for it in range(15):
    new = Pw.copy()
    for i in sel: new[i] = Pw[i] + 0.5 * (Pw[nb[i]].mean(0) - Pw[i])
    d = new - P0; L = np.linalg.norm(d, axis=1); k = L > 0.004; new[k] = P0[k] + d[k] / L[k][:, None] * 0.004; Pw = new
mv = np.zeros(n, bool); mv[sel] = True; P2 = np.where(mv[inv][:, None], Pw[inv], P)
print('front-edge vertices eased: %d, largest move %.1f mm' % (len(sel), np.abs(Pw - P0).max() * 1000))
bl = bytearray(blob)
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    off = len(bl); bl.extend(data.tobytes())
    g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
    return len(g.accessors) - 1
p32 = P2.astype('<f4'); ip = addacc(p32, 'VEC3', 5126, 34962, p32.min(0).tolist(), p32.max(0).tolist())
for p in pr: p.attributes.POSITION = ip
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst); print('saved', dst)
