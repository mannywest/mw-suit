#!/usr/bin/env python3
"""Smooth a small area of chosen cloth materials WITHOUT flipping any triangle.
    python3 scripts/smooth_local.py IN.glb OUT.glb "xmin,xmax,ymin,ymax,zmin,zmax" MAT1[,MAT2] [cap_mm=4] [iters=12]
Inside the box (metres): interior points ease toward the average of their neighbours; open-edge points ease along the edge.
A move is only accepted if every triangle touching the point keeps facing the same way and the point stays within cap_mm of where it started."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from pygltflib import Accessor, BufferView
src, dst, boxs, mats = sys.argv[1:5]; cap = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.004; iters = int(sys.argv[6]) if len(sys.argv) > 6 else 12
x0, x1, y0, y1, z0, z1 = [float(v) for v in boxs.split(',')]; mats = mats.split(',')
g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives; P2 = P.copy(); report = []
def tri_n(Pp, F):
    n = np.cross(Pp[F[:, 1]] - Pp[F[:, 0]], Pp[F[:, 2]] - Pp[F[:, 0]]); return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
for i, p in enumerate(pr):
    if g.materials[p.material].name not in mats: continue
    F = Fs[i]; key = np.round(P / 1e-4).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    W = inv[F]; n = len(first); Pw = P[first].copy(); P0 = Pw.copy()
    E = np.vstack([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]); Es = np.sort(E, 1); u, c = np.unique(Es, axis=0, return_counts=True)
    nbr = [set() for _ in range(n)]; bnb = [set() for _ in range(n)]
    for a, b in E: nbr[a].add(b); nbr[b].add(a)
    for a, b in u[c == 1]: bnb[a].add(b); bnb[b].add(a)
    inbox = (Pw[:, 0] >= x0) & (Pw[:, 0] <= x1) & (Pw[:, 1] >= y0) & (Pw[:, 1] <= y1) & (Pw[:, 2] >= z0) & (Pw[:, 2] <= z1)
    used = np.zeros(n, bool); used[W.ravel()] = True; cand = np.nonzero(inbox & used)[0]
    inc = [[] for _ in range(n)]
    for t, f in enumerate(W):
        for v in f: inc[v].append(t)
    nrm0 = tri_n(Pw, W); moved = 0
    for it in range(iters):
        for v in cand:
            if len(nbr[v]) < 2: continue
            tgt = Pw[list(bnb[v])].mean(0) if len(bnb[v]) == 2 else (Pw[list(nbr[v])].mean(0) if not bnb[v] else None)
            if tgt is None: continue
            new = Pw[v] + 0.5 * (tgt - Pw[v]); d = new - P0[v]; L = np.linalg.norm(d)
            if L > cap: new = P0[v] + d / L * cap
            old = Pw[v].copy(); Pw[v] = new; tn = tri_n(Pw, W[inc[v]])
            if (np.einsum('ij,ij->i', tn, nrm0[inc[v]]) < 0.7).any(): Pw[v] = old
    mv = (np.linalg.norm(Pw - P0, axis=1) > 1e-5); moved = int(mv.sum())
    P2[mv[inv]] = Pw[inv][mv[inv]]
    report.append('%s: %d points in box, %d moved, largest move %.1f mm' % (g.materials[p.material].name, len(cand), moved, np.linalg.norm(Pw - P0, axis=1).max() * 1000))
print('\n'.join(report))
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
