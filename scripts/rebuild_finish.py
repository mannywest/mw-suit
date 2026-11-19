#!/usr/bin/env python3
"""Put the rebuilt closed shell into a suit GLB.  python3 scripts/rebuild_finish.py OLD.glb SHELL.npz OUT.glb
Outer-side triangles keep the wool material with UVs copied from the nearest old cloth triangle; inner-side triangles get Jacket_Lining."""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from pygltflib import GLTF2, Accessor, BufferView, Material, PbrMetallicRoughness, Primitive, Attributes
from seam5 import rd
from seam2 import tris
from scipy.spatial import cKDTree
old, shp, dst = sys.argv[1:4]
g = GLTF2().load(old); blob = g.binary_blob(); bl = bytearray(blob); mesh = g.meshes[1]
wool = next(i for i, p in enumerate(mesh.primitives) if g.materials[p.material].name == 'Jacket_Wool'); wp = mesh.primitives[wool]
P = rd(g, blob, wp.attributes.POSITION, 3); U0 = rd(g, blob, wp.attributes.TEXCOORD_0, 2); U1 = rd(g, blob, wp.attributes.TEXCOORD_1, 2); F = tris(g, wp.indices)
A, B, C = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]; nrm = np.cross(B - A, C - A); ar = np.linalg.norm(nrm, axis=1); nrm /= np.maximum(ar, 1e-12)[:, None]
ns = np.maximum(3, np.ceil(ar / 2.5e-5).astype(int)); ids = np.repeat(np.arange(len(F)), ns); r = np.random.rand(len(ids), 2); fl = r.sum(1) > 1; r[fl] = 1 - r[fl]
S = A[ids] + (B[ids] - A[ids]) * r[:, :1] + (C[ids] - A[ids]) * r[:, 1:]; tree = cKDTree(S)
d = np.load(shp); V, Fn, N = d['v'].astype(float), d['f'].astype(int), d['n'].astype(float)
cen = V[Fn].mean(1); _, k = tree.query(cen); t = ids[k]
fn = np.cross(V[Fn[:, 1]] - V[Fn[:, 0]], V[Fn[:, 2]] - V[Fn[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
raw = np.where((fn * nrm[t]).sum(1) > 0, 1.0, -1.0)      # facing the same way as the old cloth = outer face
ct = cKDTree(cen); _, nb = ct.query(cen, k=24)
for _ in range(3):                                         # neighbours that face the same way vote, so lone flecks flip to the majority
    same = (fn[nb] * fn[:, None, :]).sum(2) > 0.5; raw = np.sign((raw[nb] * same).sum(1) + 0.01 * raw)
side = raw > 0
if os.environ.get('RAYSIDE', '1') == '1':                  # arbiter: a ray out of an outer face escapes the garment; one out of an inner face hits the far wall
    import bpy; from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(x) for x in V.tolist()], [tuple(x) for x in Fn.tolist()])
    hit = np.zeros(len(Fn), bool)
    for i in range(len(Fn)):
        o = cen[i] + fn[i] * 0.0008; r_ = bvh.ray_cast(Vector(o), Vector(fn[i]), 0.35); hit[i] = r_[0] is not None
    ray_side = ~hit; dis = (ray_side != side); print('ray vs vote disagree:', int(dis.sum()), 'of', len(Fn))
    L = np.where(dis, 0.0, np.where(side, 1.0, -1.0))          # keep only labels both tests agree on, then grow them over the doubtful ones
    same = (fn[nb] * fn[:, None, :]).sum(2) > 0.6
    for _ in range(60):
        unk = L == 0
        if not unk.any(): break
        v_ = (L[nb] * same).sum(1); L = np.where(unk & (v_ != 0), np.sign(v_), L)
    side = np.where(L == 0, side, L > 0); print('doubtful left after growing:', int((L == 0).sum()))

# rim smoothing: vertices shared by outer-labelled and inner-labelled triangles form the cloth's edge (hem, front edge, cuffs). Smooth them ALONG the edge only.
if os.environ.get('RIM', '0') == '1':
    nV = len(V); cnt = np.zeros((nV, 2), int); np.add.at(cnt[:, 0], Fn[side].ravel(), 1); np.add.at(cnt[:, 1], Fn[~side].ravel(), 1); rim = (cnt[:, 0] > 0) & (cnt[:, 1] > 0)
    e_ = np.vstack([Fn[:, [0, 1]], Fn[:, [1, 2]], Fn[:, [2, 0]]]); e_ = e_[rim[e_[:, 0]] & rim[e_[:, 1]]]; e_ = np.unique(np.sort(e_, axis=1), axis=0)
    deg = np.bincount(e_.ravel(), minlength=nV)
    for _ in range(int(os.environ.get('RIMIT', '20'))):
        acc = np.zeros_like(V); np.add.at(acc, e_[:, 0], V[e_[:, 1]]); np.add.at(acc, e_[:, 1], V[e_[:, 0]])
        m_ = rim & (deg > 0); V[m_] = 0.5 * V[m_] + 0.5 * acc[m_] / deg[m_][:, None]
    print('rim vertices smoothed:', int(rim.sum()))
print('new tris', len(Fn), ' outer side %d  inner side %d' % (side.sum(), (~side).sum()))
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
nv = len(P); ed = np.vstack([F[:, [0, 1]], F[:, [1, 2]]]); _, comp = connected_components(coo_matrix((np.ones(len(ed)), (ed[:, 0], ed[:, 1])), shape=(nv, nv)), directed=False)
isl_of_tri = comp[F[:, 0]]; print('uv islands', len(np.unique(isl_of_tri)))
itrees = {}
for i in np.unique(isl_of_tri):
    m = isl_of_tri[ids] == i; itrees[i] = (cKDTree(S[m]), ids[m])
def corner_tri(pts, isl):                 # nearest old triangle INSIDE the same island
    out = np.zeros(len(pts), int)
    for i in np.unique(isl):
        m = isl == i; _, kk = itrees[i][0].query(pts[m]); out[m] = itrees[i][1][kk]
    return out
vtrees = {}
for i in np.unique(isl_of_tri):
    vv = np.unique(F[isl_of_tri == i]); vtrees[i] = (cKDTree(P[vv]), vv)
def uv_knn(pts, isl, k=4):                # smooth UV: inverse-distance blend of the nearest old vertices of the same island
    a0 = np.zeros((len(pts), 2)); a1 = np.zeros((len(pts), 2))
    for i in np.unique(isl):
        m = np.where(isl == i)[0]; tr, vv = vtrees[i]; kk = min(k, len(vv)); dd, jj = tr.query(pts[m], k=kk)
        if kk == 1: dd, jj = dd[:, None], jj[:, None]
        w = 1.0 / np.maximum(dd, 1e-4) ** 2; w /= w.sum(1, keepdims=True); gv = vv[jj]
        a0[m] = (w[:, :, None] * U0[gv]).sum(1); a1[m] = (w[:, :, None] * U1[gv]).sum(1)
    return a0, a1
def uvfor(pts, tt):                      # barycentric of point projected on old triangle tt, applied to UVs
    a, b, c = P[F[tt, 0]], P[F[tt, 1]], P[F[tt, 2]]; v0, v1, v2 = b - a, c - a, pts - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-20); w1 = (d11 * d20 - d01 * d21) / den; w2 = (d00 * d21 - d01 * d20) / den
    w1 = np.clip(w1, 0, 1); w2 = np.clip(w2, 0, 1); sm = w1 + w2; w1 = np.where(sm > 1, w1 / np.maximum(sm, 1e-9), w1); w2 = np.where(sm > 1, w2 / np.maximum(sm, 1e-9), w2); w0 = 1 - w1 - w2
    f = F[tt]; return w0[:, None] * U0[f[:, 0]] + w1[:, None] * U0[f[:, 1]] + w2[:, None] * U0[f[:, 2]], w0[:, None] * U1[f[:, 0]] + w1[:, None] * U1[f[:, 1]] + w2[:, None] * U1[f[:, 2]]
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    off = len(bl); bl.extend(data.tobytes()); g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx)); return len(g.accessors) - 1
lin = Material(name='Jacket_Lining', pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[0.11, 0.15, 0.25, 1], metallicFactor=0.0, roughnessFactor=0.9), doubleSided=False)
g.materials.append(lin); li = len(g.materials) - 1; new = []
for sel, mat, dbl in ((side, wp.material, None), (~side, li, None)):
    ti = np.where(sel)[0]; vi = Fn[ti]; Pp = V[vi].reshape(-1, 3); Nn = N[vi].reshape(-1, 3); u0, u1 = uv_knn(Pp, np.repeat(isl_of_tri[t[ti]], 3))
    # UV1 is the fabric tile: the old model projects it in world space at 30 mm per tile, so do exactly that (no stretch by construction)
    nf = np.abs(np.repeat(fn[ti], 3, axis=0)); ax = nf.argmax(1); x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    u1 = np.where(ax[:, None] == 0, np.c_[-33.33 * z, -33.33 * y], np.where(ax[:, None] == 2, np.c_[33.33 * x, -33.33 * y], np.c_[33.33 * x, -33.33 * z]))
    u1 = u1.astype(float)
    key = np.round(np.hstack([Pp * 1e5, Nn * 1e3, u0 * 1e4, u1 * 1e4])).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)   # weld identical corners
    Pp, Nn, u0, u1 = Pp[first], Nn[first], u0[first], u1[first]; idx = inv.reshape(-1).astype('<u4')
    # shading normals from this layer's own faces only (area-weighted), so edge vertices are not skewed by the other layer
    Nold = Nn / np.maximum(np.linalg.norm(Nn, axis=1), 1e-12)[:, None]
    fa = np.cross(Pp[idx.reshape(-1, 3)[:, 1]] - Pp[idx.reshape(-1, 3)[:, 0]], Pp[idx.reshape(-1, 3)[:, 2]] - Pp[idx.reshape(-1, 3)[:, 0]]); Nn = np.zeros_like(Pp)
    for k_ in range(3): np.add.at(Nn, idx.reshape(-1, 3)[:, k_], fa)
    ln = np.linalg.norm(Nn, axis=1); Nn = np.where((ln > 1e-9)[:, None], Nn / np.maximum(ln, 1e-12)[:, None], Nold)
    pa = addacc(Pp.astype('<f4'), 'VEC3', 5126, 34962, Pp.min(0).tolist(), Pp.max(0).tolist()); na = addacc(Nn.astype('<f4'), 'VEC3', 5126, 34962)
    ua = addacc(u0.astype('<f4'), 'VEC2', 5126, 34962); ub = addacc(u1.astype('<f4'), 'VEC2', 5126, 34962)
    ia = addacc(idx, 'SCALAR', 5125, 34963)
    new.append(Primitive(attributes=Attributes(POSITION=pa, NORMAL=na, TEXCOORD_0=ua, TEXCOORD_1=ub), indices=ia, material=mat, mode=4))
mesh.primitives[wool:wool + 1] = new
if g.materials[wp.material].doubleSided: g.materials[wp.material].doubleSided = False
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst); print('saved', dst)
