# Repair step 2: rebuild the peak lapel surface (Jacket_Lapel_Peak, both sides).
# Input : MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb   (not modified)
# Output: new file given as argv[2]
# - removes the old lapel pieces (incl. the inner strip and the flat panels inside the neck)
# - new lapel: same outline, inner edge follows the jacket front edge, smooth surface taken from the notch lapel,
#   closed edge walls down to the jacket (no see-through gaps under the peak tips)
# - the peak collar triangles, all other primitives and all existing vertex data are unchanged
import sys, collections
import numpy as np
sys.path.insert(0, '/Users/mannywest/Projects/mw-suit/scripts/check'); sys.path.insert(0, '/Users/mannywest/Projects/mw-suit/scripts')
from common import load, depthmap
from pygltflib import Accessor, BufferView
from scipy.ndimage import gaussian_filter

src, dst = sys.argv[1], sys.argv[2]
g, blob, P, N, U0, U1, Fs = load(src)
pr = g.meshes[1].primitives
ipk = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Lapel_Peak'][0]
Fb, Fp = Fs[0], Fs[ipk]

# --- split peak primitive: two big lapel pieces vs collar fragments
par = np.arange(len(P))
def f(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for t in Fp:
    for a, b in ((t[0], t[1]), (t[1], t[2])):
        ra, rb = f(a), f(b)
        if ra != rb: par[ra] = rb
lab = np.array([f(t[0]) for t in Fp]); top2 = [k for k, _ in collections.Counter(lab).most_common(2)]
lapel = np.isin(lab, top2)
Fcollar = Fp[~lapel]
print('old lapel tris', lapel.sum(), 'collar tris kept', len(Fcollar))

# --- depth maps (front view): u=x, v=y, value = true z (frontmost)
BOX = (-0.20, 0.20, 1.08, 1.50); RES = 1000  # px per metre (1 px/mm)
W, H = int((BOX[1]-BOX[0])*RES), int((BOX[3]-BOX[2])*RES)
Q = P * [-1, 1, -1]
zbody, _, s = depthmap(Q, Fb, BOX, W, H)
T = P[Fp[lapel]]; n = np.cross(T[:, 1]-T[:, 0], T[:, 2]-T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True)+1e-12
front = (np.abs(n[:, 2]) > 0.3) & (T[:, :, 2].mean(1) > 0.0)       # drops the panels inside the neck
# surface shape source: the smooth notch lapel (from collarfix4, read only), front-facing parts
_g2, _b2, P2, _n2, _u0, _u1, Fs2 = load('/Users/mannywest/Projects/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4.glb')
Fn = Fs2[[i for i, p in enumerate(_g2.meshes[1].primitives) if _g2.materials[p.material].name == 'Jacket_Lapel'][0]]
Tn = P2[Fn]; nn_ = np.cross(Tn[:, 1]-Tn[:, 0], Tn[:, 2]-Tn[:, 0]); nn_ /= np.linalg.norm(nn_, axis=1, keepdims=True)+1e-12
fr = (nn_[:, 2] > 0.3) & (Tn[:, :, 2].mean(1) > 0.02)
zlap, _, _ = depthmap(P2*[-1, 1, -1], Fn[fr], BOX, W, H)
def smooth_fill(z, sig):
    m = np.isfinite(z); z0 = np.where(m, z, 0.0)
    a = gaussian_filter(z0, sig); b = gaussian_filter(m.astype(float), sig)
    return a / np.maximum(b, 1e-9), b
zl_s, wl = smooth_fill(zlap, 6)      # 6 mm smoothing
zl_s2, _ = smooth_fill(zlap, 25)     # wide fill for points just outside the old lapel
zl_s = np.where(wl > 0.05, zl_s, zl_s2)
zb_s, wb = smooth_fill(zbody, 2)
def samp(img, x, y):
    c = np.clip(((x-BOX[0])*s-.5), 0, W-1.001); r = np.clip(((BOX[3]-y)*s-.5), 0, H-1.001)
    c0 = c.astype(int); r0 = r.astype(int); fc = c-c0; fr = r-r0
    return (img[r0, c0]*(1-fc)*(1-fr)+img[r0, c0+1]*fc*(1-fr)+img[r0+1, c0]*(1-fc)*fr+img[r0+1, c0+1]*fc*fr)
def body_z(x, y):
    ok = samp(np.isfinite(zbody).astype(float), x, y) > 0.999
    z = samp(np.where(np.isfinite(zbody), zbody, 0.0), x, y); return np.where(ok, z, np.nan)

# --- outline (|x|, y), from the earlier peak rebuild; inner edge = jacket front edge per side
ys = np.array([1.14,1.16,1.18,1.20,1.22,1.24,1.26,1.28,1.30,1.32,1.34,1.36,1.38])
xo = np.array([0.035,0.051,0.062,0.072,0.080,0.092,0.102,0.109,0.116,0.125,0.129,0.137,0.144])
po = np.polyfit(ys, xo, 3)
def body_opening(side):
    V = np.unique(Fb.ravel()); V = V[(np.sign(P[V, 0]) == side) & (P[V, 2] > 0.0)]
    yy = np.arange(1.12, 1.445, 0.01); xx = []
    for y in yy:
        m = np.abs(P[V, 1]-y) < 0.006; xx.append(np.abs(P[V[m], 0]).min())
    return np.polyfit(yy, xx, 3)
B0y, Gy = 1.115, 1.445
G_x = 0.063; Hpt = (0.085, 1.401); Cpt = (0.137, 1.412); Tp = np.array([0.155, 1.422])
Nu, Nv = 64, 16
def arc(Pc): d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Pc, axis=0), axis=1))]; return d/d[-1]
def resample(Pc, k):
    sa = arc(Pc); t = np.linspace(0, 1, k); return np.c_[np.interp(t, sa, Pc[:, 0]), np.interp(t, sa, Pc[:, 1])]

newP, newN, newU0, newU1, newT = [], [], [], [], []
base = len(P)
def vnorm(Pv, Tv):
    fn = np.cross(Pv[Tv[:, 1]]-Pv[Tv[:, 0]], Pv[Tv[:, 2]]-Pv[Tv[:, 0]]); nn = np.zeros_like(Pv)
    for k in range(3): np.add.at(nn, Tv[:, k], fn)
    ln = np.linalg.norm(nn, axis=1, keepdims=True); nn = np.where(ln > 1e-9, nn/np.maximum(ln, 1e-12), [0.0, 0.0, 1.0])
    return nn/np.linalg.norm(nn, axis=1, keepdims=True)
for side in (-1, 1):
    pi_ = body_opening(side)
    inner = lambda y: np.polyval(pi_, y)
    B0 = np.array([inner(B0y), B0y]); G = np.array([inner(Gy) if abs(inner(Gy)-G_x) < 0.01 else G_x, Gy])
    yA = np.linspace(B0y, Gy, 80); A = np.c_[inner(yA), yA]; A[-1] = G
    yB = np.linspace(1.14, 1.38, 50)
    B = np.vstack([B0, np.c_[np.polyval(po, yB), yB], [0.1445, 1.39], Tp])
    top = np.array([G, Hpt, Cpt, Tp])
    Au = resample(A, Nu+1); Bu = resample(B, Nu+1); Tv = resample(top, Nv+1)
    u = np.linspace(0, 1, Nu+1)[:, None, None]; v = np.linspace(0, 1, Nv+1)[None, :, None]
    Pg = (1-v)*Au[:, None, :]+v*Bu[:, None, :]+u*(Tv[None, :, :]-((1-v)*G+v*Tp))
    X = side*Pg[:, :, 0]; Y = Pg[:, :, 1]
    Z = samp(zl_s, X, Y)
    bz = body_z(X, Y)
    bz = np.where(bz > Z + 0.004, np.nan, bz)   # ignore the other front panel where it crosses over (below the button)
    Z = np.where(np.isfinite(bz), np.maximum(Z, bz+0.003), Z)   # always >= 3 mm above jacket
    Z = gaussian_filter(Z, (1.5, 1.0), mode='nearest')
    Z = np.where(np.isfinite(bz), np.maximum(Z, bz+0.0025), Z)
    Pl = np.dstack([X, Y, Z]).reshape(-1, 3)
    T = []
    for i in range(Nu):
        for j in range(Nv):
            a = i*(Nv+1)+j; b = a+1; c = a+Nv+1; d = c+1
            T += [[a, c, b], [b, c, d]]
    T = np.array(T)
    nn = vnorm(Pl, T)
    if nn[:, 2].mean() < 0: T = T[:, [0, 2, 1]]; nn = -nn
    # UV: affine fit (x,y)->uv from the old lapel vertices of this side
    lv = np.unique(Fp[lapel].ravel()); lv = lv[np.sign(P[lv, 0]) == side]
    M = np.c_[P[lv, 0], P[lv, 1], np.ones(len(lv))]
    c0 = np.linalg.lstsq(M, U0[lv], rcond=None)[0]; c1 = np.linalg.lstsq(M, U1[lv], rcond=None)[0]
    uvm = lambda Pv: np.c_[Pv[:, 0], Pv[:, 1], np.ones(len(Pv))]
    # edge walls: boundary loop of the grid, each point dropped down to the jacket (or 4 mm)
    idx = lambda i, j: i*(Nv+1)+j
    loop = [idx(i, 0) for i in range(Nu+1)] + [idx(Nu, j) for j in range(1, Nv+1)] + [idx(i, Nv) for i in range(Nu-1, -1, -1)]
    E = Pl[loop].copy(); eb = body_z(E[:, 0], E[:, 1]); eb = np.where(eb > E[:, 2] + 0.002, np.nan, eb)
    drop = np.where(np.isfinite(eb) & (eb < E[:, 2]), np.minimum(eb-0.001, E[:, 2]-0.002), E[:, 2]-0.004)
    lim = np.full(len(loop), 0.040); lim[:Nu+1] = 0.006   # inner edge (roll line): short wall; top/outer: up to 40 mm
    drop = np.maximum(drop, E[:, 2]-lim)
    Wt = np.vstack([E, np.c_[E[:, :2], drop]]); k = len(loop)
    WT = []
    for q in range(k-1): WT += [[q, q+1, k+q+1], [q, k+q+1, k+q]]
    WT = np.array(WT)
    # orient walls outward (away from lapel centre in x,y)
    cen = Pl[:, :2].mean(0); wn = np.cross(Wt[WT[:, 1]]-Wt[WT[:, 0]], Wt[WT[:, 2]]-Wt[WT[:, 0]]); wc = Wt[WT].mean(1)
    fl = ((wc[:, :2]-cen)*wn[:, :2]).sum(1) < 0; WT[fl] = WT[fl][:, [0, 2, 1]]
    wnv = vnorm(Wt, WT)
    o = base + sum(len(x) for x in newP)
    newP += [Pl, Wt]; newN += [nn, wnv]
    newU0 += [uvm(Pl)@c0, uvm(Wt)@c0]; newU1 += [uvm(Pl)@c1, uvm(Wt)@c1]
    newT += [T+o, WT+o+len(Pl)]
    print('side', side, 'grid tris', len(T), 'wall tris', len(WT), 'z range %.3f..%.3f' % (Z.min(), Z.max()),
          'gap above jacket mm min %.1f max %.1f, top row max %.1f' % (np.nanmin((Z-bz)*1000), np.nanmax((Z-bz)*1000), np.nanmax((Z-bz)[-1]*1000)))

newP = np.vstack(newP); Fnew = np.vstack(newT)
PP = np.vstack([P, newP]); NN = np.vstack([N, np.vstack(newN)]); UU0 = np.vstack([U0, np.vstack(newU0)]); UU1 = np.vstack([U1, np.vstack(newU1)])
Fpk = np.vstack([Fnew, Fcollar])
bl = bytearray(blob)
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    off = len(bl); bl.extend(data.tobytes())
    g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews)-1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
    return len(g.accessors)-1
ids = [addacc(PP.astype('<f4'), 'VEC3', 5126, 34962, PP.astype('<f4').min(0).tolist(), PP.astype('<f4').max(0).tolist()),
       addacc(NN.astype('<f4'), 'VEC3', 5126, 34962), addacc(UU0.astype('<f4'), 'VEC2', 5126, 34962), addacc(UU1.astype('<f4'), 'VEC2', 5126, 34962)]
for k, p in enumerate(pr):
    p.attributes.POSITION, p.attributes.NORMAL, p.attributes.TEXCOORD_0, p.attributes.TEXCOORD_1 = ids
pr[ipk].indices = addacc(Fpk.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
print('new verts', len(newP), 'peak tris', len(Fpk), 'saved', dst)
