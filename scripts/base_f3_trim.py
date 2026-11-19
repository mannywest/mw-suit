#!/usr/bin/env python3
"""Remove small loose cloth pieces (<300 tris) low on the jacket sides (y<0.82, |x|>0.18): the ragged flaps at the hem.
    python3 scripts/base_f3_trim.py IN.glb OUT.glb [side=+1|-1|0 for both]"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import base_e_sides as be
src, dst = sys.argv[1], sys.argv[2]; side = int(sys.argv[3]) if len(sys.argv) > 3 else 0
g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; F = Fs[ib]
key = np.round(P / 1e-4).astype(np.int64); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel(); W = inv[F]; n = inv.max() + 1
E = np.vstack([W[:, [0, 1]], W[:, [1, 2]]]); A = coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n)); nc, lab = connected_components(A, directed=False)
tl = lab[W[:, 0]]; cnt = np.bincount(tl, minlength=nc); cen = P[F].mean(1); drop = np.zeros(len(F), bool)
for c in np.nonzero((cnt > 0) & (cnt < 300))[0]:
    m = tl == c; cc = cen[m].mean(0)
    if cc[1] < 0.82 and abs(cc[0]) > 0.18 and (side == 0 or np.sign(cc[0]) == side):
        drop |= m; print('removed piece: %d tris at (%+.3f,%.3f,%+.3f)' % (cnt[c], *cc))
be.write(src, dst, [], drop); print('saved', dst, 'removed', drop.sum(), 'tris')
