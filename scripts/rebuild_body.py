#!/usr/bin/env python3
"""Rebuild the jacket cloth as ONE closed shell.  python3 scripts/rebuild_body.py IN.glb OUT.npz [R_mm=8] [vox_mm=2.5] [thick_mm=3]
Method: voxelise the old cloth surface, 'close' it (dilate by R then erode by R) so holes narrower than 2R fill, then extract the
surface of the result as a 3 mm thick closed shell (marching cubes). Old jacket is only the shape guide."""
import sys, os, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from pygltflib import GLTF2
from seam5 import rd
from seam2 import tris
from scipy import ndimage as ndi
from skimage import measure
src, out = sys.argv[1], sys.argv[2]; R = float(sys.argv[3]) / 1000 if len(sys.argv) > 3 else 0.008
V = float(sys.argv[4]) / 1000 if len(sys.argv) > 4 else 0.0025; T = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.003
g = GLTF2().load(src); blob = g.binary_blob(); mesh = g.meshes[1]
P = None; F = []
for p in mesh.primitives:
    if g.materials[p.material].name == 'Jacket_Wool':
        P = rd(g, blob, p.attributes.POSITION, 3); F.append(tris(g, p.indices))
F = np.vstack(F); used = np.unique(F); print('cloth tris', len(F), 'verts', len(used), 'bbox', P[used].min(0).round(3), P[used].max(0).round(3))
lo = P[used].min(0) - R * 3; hi = P[used].max(0) + R * 3; shp = np.ceil((hi - lo) / V).astype(int) + 1; print('grid', shp, shp.prod() / 1e6, 'M')
M = np.zeros(shp, bool); t0 = time.time()
A, B, C = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1); n = np.maximum(1, np.ceil(area / (V * V * 0.25)).astype(int))
for k in np.unique(n):
    sel = np.where(n == k)[0]
    for _ in range(k):
        r1, r2 = np.random.rand(2, len(sel)); fl = r1 + r2 > 1; r1[fl] = 1 - r1[fl]; r2[fl] = 1 - r2[fl]
        pt = A[sel] + (B[sel] - A[sel]) * r1[:, None] + (C[sel] - A[sel]) * r2[:, None]; ij = ((pt - lo) / V).astype(int); M[ij[:, 0], ij[:, 1], ij[:, 2]] = True
print('voxelised', M.sum(), 'cells', round(time.time() - t0, 1), 's')
dS = ndi.distance_transform_edt(~M, sampling=V)          # distance to old surface
Dil = dS < R                                              # dilate by R
dOut = ndi.distance_transform_edt(Dil, sampling=V)        # distance to outside of dilated region
Cl = (dOut > R) | M                                       # erode by R (keep old surface) => closed surface skeleton
dC = ndi.distance_transform_edt(~Cl, sampling=V)
field = dC - T / 2
vt, ft, nt, _ = measure.marching_cubes(field, 0.0, spacing=(V, V, V), allow_degenerate=True); vt = vt + lo
print('new shell verts', len(vt), 'tris', len(ft), 'time', round(time.time() - t0, 1), 's')
np.savez_compressed(out, v=vt.astype('f4'), f=ft.astype('u4'), n=nt.astype('f4'))
# watertight check: every edge used by exactly two triangles
e = np.sort(np.vstack([ft[:, [0, 1]], ft[:, [1, 2]], ft[:, [2, 0]]]), axis=1); _, c = np.unique(e, axis=0, return_counts=True)
print('edges used once (open):', int((c == 1).sum()), ' used >2 (non-manifold):', int((c > 2).sum()))
