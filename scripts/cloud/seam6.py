"""seam6: rear collar seam cut along ONE smooth curve K(x), with overlap so no gaps.
Input: MW_Tailleur_suit_v4_blender_collarfix2.glb (state before seam5). Writes a new file.
Coordinates (glTF): x left/right, y up, z<0 = back of the jacket.
"""
import numpy as np, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from pygltflib import GLTF2, Accessor, BufferView
from seam5 import rd
from seam2 import tris

K0 = 1.4400          # seam height at the centre back (m): just above the collar's lowest edge (1.4399)
X1, X2 = 0.095, 0.125  # level until X1, then curves down to join the shoulder line at X2
SH_SLOPE = -0.40     # shoulder-line slope (dy/d|x|), measured from the back silhouette
YSH = 1.4335         # shoulder-line height at X2 (measured: 1.4331 / 1.4341 left / right)
OVL = 0.003          # collar runs this far below the seam where the back hides it
OVLB = 0.012         # back panel runs this far up behind the collar where the collar hides it
XB = 0.095           # the back panel is only cut for |x| < XB; further out its own rounded top is the seam
PUSH = 0.0015        # hidden back panel tucked this far inward behind the collar (stops flicker)

def ss(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def K(x, ybt2):
    a = np.abs(x); t = np.clip((a - X1) / (X2 - X1), 0, 1); L = X2 - X1
    h00 = 2*t**3 - 3*t**2 + 1; h01 = 1 - h00; h11 = t**3 - t**2
    k = h00 * K0 + h01 * ybt2 + h11 * L * SH_SLOPE
    return np.where(a <= X1, K0, np.where(a <= X2, k, ybt2 + SH_SLOPE * (a - X2)))

def wcol(x):  # 1 where the collar is in front of the back at the seam, 0 where the back is in front
    return 1 - ss((np.abs(x) - 0.086) / 0.006)  # measured: collar in front up to |x|=0.088

def main(src, dst):
    g = GLTF2().load(src); blob = g.binary_blob(); pr = g.meshes[1].primitives; at = pr[0].attributes
    P = rd(g, blob, at.POSITION, 3); Nn = rd(g, blob, at.NORMAL, 3)
    U0 = rd(g, blob, at.TEXCOORD_0, 2); U1 = rd(g, blob, at.TEXCOORD_1, 2)
    n = len(P)
    idx = {p.indices: k for k, p in enumerate(pr)}
    Fb, Fn, Fp = (tris(g, pr[k].indices) for k in range(3))
    # shoulder height at X2 from the back body itself (highest rear body point in that column)
    ybt2 = YSH
    # close the one-triangle tear in the back panel right of centre (open edges 26334-26176 and 26334-26182)
    a_, b_, c_ = 26334, 26176, 26182
    for t in Fb:  # orient the new triangle against the existing neighbour across edge a_-b_
        if a_ in t and b_ in t:
            i = list(t).index(a_); fwd = t[(i+1) % 3] == b_
            break
    Fb = np.vstack([Fb, [[b_, a_, c_] if fwd else [a_, b_, c_]]])
    # ...and the wedge next to it (open edges 26185-26182 and 26172-26184), which left a slot behind the collar
    assert not fwd
    Fb = np.vstack([Fb, [[26185, 26182, 26172], [26172, 26182, 26176]]])
    print('tear filled with 3 triangles')
    Kf = lambda x: K(x, ybt2)

    # 1) where the collar is in front, tuck the hidden part of the back panel (above the seam) 1.5 mm
    #    further in, so the two surfaces never flicker through each other. Purely position-based, so
    #    duplicate vertices at the same spot move together; the visible back below the seam does not move.
    bv = np.unique(Fb); bv = bv[bv < n]
    x, y, z = P[bv, 0], P[bv, 1], P[bv, 2]
    w = (z < 0) * wcol(x) * ss((y - Kf(x)) / 0.003) * (np.abs(x) < XB)
    P[bv, 2] += PUSH * w
    print('back-panel verts tucked in behind collar:', int((w > 0).sum()))

    newP, newN, newU0, newU1 = [], [], [], []; cache = {}
    def mk(a, b, t, key):
        if key in cache: return cache[key]
        newP.append(P[a]*(1-t) + P[b]*t); v = Nn[a]*(1-t) + Nn[b]*t; newN.append(v/(np.linalg.norm(v)+1e-12))
        newU0.append(U0[a]*(1-t) + U0[b]*t); newU1.append(U1[a]*(1-t) + U1[b]*t)
        cache[key] = n + len(newP) - 1; return cache[key]

    def clip(T, gfun, inreg, tag):
        out = []; nc = 0
        for t in T:
            pp = P[t]
            if not inreg(pp): out.append(tuple(t)); continue
            gv = gfun(pp)
            if (gv >= 0).all(): out.append(tuple(t)); continue
            nc += 1
            if (gv < 0).all(): continue
            poly = []
            for i in range(3):
                a, b = t[i], t[(i+1) % 3]; ga, gb = gv[i], gv[(i+1) % 3]
                if ga >= 0: poly.append(a)
                if (ga >= 0) != (gb >= 0):
                    lo, hi = 0.0, 1.0
                    for _ in range(40):
                        mid = (lo+hi)/2; q = P[a]*(1-mid) + P[b]*mid
                        if (gfun(q[None])[0] >= 0) == (ga >= 0): lo = mid
                        else: hi = mid
                    key = (tag, min(a, b), max(a, b))
                    tt = (lo+hi)/2 if a < b else 1-(lo+hi)/2
                    poly.append(mk(min(a, b), max(a, b), tt, key))
            for i in range(1, len(poly)-1): out.append((poly[0], poly[i], poly[i+1]))
        print(tag, 'triangles cut/removed:', nc); return np.array(out)

    # region: back of the neck, inside the collar width
    def reg(pp): c = pp.mean(0); return (c[2] < 0) and (abs(c[0]) < X2) and (pp[:, 1].min() > 1.40)
    def regb(pp): c = pp.mean(0); return (c[2] < 0) and (abs(c[0]) < XB) and (pp[:, 1].min() > 1.40)
    # body keeps y <= K (+overlap where the collar is in front and hides it)
    gb = lambda q: (Kf(q[:, 0]) + OVLB * wcol(q[:, 0])) - q[:, 1]
    # collar keeps y >= K (-overlap where the body is in front and hides it)
    gc = lambda q: q[:, 1] - (Kf(q[:, 0]) - OVL * (1 - wcol(q[:, 0])))
    Nb = clip(Fb, gb, regb, 'body')
    Nn2 = clip(Fn, gc, reg, 'collar')  # notch and peak share the same cut points
    Np2 = clip(Fp, gc, reg, 'collar')

    # 2) shoulder spikes: thin peak-lapel slivers at |x|~0.15 that hang below the shoulder line at the back
    PP = np.vstack([P, np.array(newP)]) if newP else P
    cen = PP[Np2].mean(1)
    spike = (np.abs(cen[:, 0]) > 0.14) & (cen[:, 2] < 0) & (cen[:, 1] < 1.425) & (cen[:, 1] > 1.40)
    print('spike triangles removed:', int(spike.sum()))
    Np2 = Np2[~spike]

    add = len(newP); print('new vertices', add)
    A = [PP, np.vstack([Nn, np.array(newN)]), np.vstack([U0, np.array(newU0)]), np.vstack([U1, np.array(newU1)])]
    bl = bytearray(blob)
    def addacc(data, typ, ctype, target, mn=None, mx=None):
        while len(bl) % 4: bl.append(0)
        off = len(bl); bl.extend(data.tobytes())
        g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
        g.accessors.append(Accessor(bufferView=len(g.bufferViews)-1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
        return len(g.accessors)-1
    ids = [addacc(A[0].astype('<f4'), 'VEC3', 5126, 34962, A[0].min(0).tolist(), A[0].max(0).tolist()),
           addacc(A[1].astype('<f4'), 'VEC3', 5126, 34962), addacc(A[2].astype('<f4'), 'VEC2', 5126, 34962),
           addacc(A[3].astype('<f4'), 'VEC2', 5126, 34962)]
    news = [Nb, Nn2, Np2]
    for k, p in enumerate(pr):
        p.attributes.POSITION, p.attributes.NORMAL, p.attributes.TEXCOORD_0, p.attributes.TEXCOORD_1 = ids
        if k < 3:
            p.indices = addacc(news[k].astype('<u4').ravel(), 'SCALAR', 5125, 34963)
    g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
    print('saved', dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
