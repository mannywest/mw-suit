# Repair step 2d = step 2c (one-piece collar) + jacket body lifted where the shirt pokes through at the back shoulders.
# Repair step 2c: ONE-PIECE peak collar (Jacket_Lapel_Peak, both sides).
# Input : MW_Tailleur_suit_v4_blender_collarfix4_peak_step2b.glb  (re-derived from _peak_only via this script's own lapel code; not modified)
# Output: new file given as argv[2]
# Lapels, gorge line, peak tips, edge walls: identical code to peak_step2b.py (lapels kept).
# Collar: ALL old collar triangles are dropped (no joins to old collar parts). One single grid (one connected surface) runs
#   from the left lapel gorge/collar point, round the back of the neck, to the right lapel gorge/collar point.
#   Its two front ends reuse the exact lapel top-edge (gorge) points. Shape comes from smooth curves, not from old collar pieces.
import sys, collections
import numpy as np
sys.path.insert(0, '/home/claude/work/scripts/check'); sys.path.insert(0, '/home/claude/work/scripts')
from common import load, depthmap
from pygltflib import Accessor, BufferView
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

src, dst = sys.argv[1], sys.argv[2]
g, blob, P, N, U0, U1, Fs = load(src)
pr = g.meshes[1].primitives
ipk = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Lapel_Peak'][0]
Fb, Fp = Fs[0], Fs[ipk]

# --- shirt clearance (step 2d): the shirt yoke is higher than the jacket behind the neck (white patches in renders). Shirt stays untouched;
#     the jacket body is raised there (smooth, feathered, shirt + 2 mm), BEFORE the lapel/collar are fitted so the collar rides the corrected body.
from scipy.ndimage import gaussian_filter, maximum_filter
from seam5 import rd as _rd
from seam2 import tris as _tris
_sh = [m for m in g.meshes if m.name == 'Shirt'][0].primitives[0]
_PS = _rd(g, blob, _sh.attributes.POSITION, 3); _FS = _tris(g, _sh.indices); _FS = _FS[_PS[_FS][:, :, 1].min(1) > 1.30]
_B = (-0.19, 0.19, -0.12, 0.09); _S = 2000; _W = int((_B[1]-_B[0])*_S); _H = int((_B[3]-_B[2])*_S)
_Hs, _, _hs = depthmap(_PS[:, [0, 2, 1]]*[-1, 1, -1], _FS, _B, _W, _H)
_vb = np.unique(Fb.ravel()); _vb = _vb[(P[_vb, 1] > 1.30) & (np.abs(P[_vb, 0]) < 0.185) & (P[_vb, 2] > -0.115) & (P[_vb, 2] < 0.085)]
_r = np.hypot(P[_vb, 0], P[_vb, 2]+0.005); _vb = _vb[_r > 0.085]                        # not inside the neck opening (shirt collar belongs there)
_ci = np.clip(((P[_vb, 0]-_B[0])*_hs-.5).astype(int), 0, _W-1); _ri = np.clip(((_B[3]-P[_vb, 2])*_hs-.5).astype(int), 0, _H-1)
_hs_at = _Hs[_ri, _ci]; _raw = np.where(np.isfinite(_hs_at), np.maximum(0, _hs_at+0.002-P[_vb, 1]), 0)
_LIFT_N = int((_raw > 0.0003).sum())
if _LIFT_N:
    _Lg = np.zeros((_H, _W)); np.maximum.at(_Lg, (_ri, _ci), _raw)
    _Lg = gaussian_filter(maximum_filter(_Lg, size=int(0.032*_hs)), 0.010*_hs)*1.35           # widen 7 mm each way, feather 4 mm, small safety factor
    _lift = np.minimum(_Lg[_ri, _ci], 0.012)
    P[_vb, 1] += _lift
    print('SHIRT CLEARANCE: %d body vertices raised (max %.1f mm, mean of raised %.1f mm)' % ((_lift > 1e-4).sum(), _lift.max()*1000, _lift[_lift > 1e-4].mean()*1000))

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
# cut the ragged front collar ends: keep only collar triangles behind ZC
ZC = -0.035
cz = P[Fcollar][:, :, 2].max(1)
Fkeep = Fcollar[cz < ZC]
Fcut = Fcollar[cz >= ZC]
# tiny body slivers left under the old collar end (they poke through the new collar band): remove
Tb = P[Fb]; area = np.linalg.norm(np.cross(Tb[:, 1]-Tb[:, 0], Tb[:, 2]-Tb[:, 0]), axis=1)/2; cb = Tb.mean(1)
sliver = (area < 10e-6) & (cb[:, 1] > 1.40) & (cb[:, 1] < 1.42) & (np.abs(cb[:, 0]) > 0.11) & (np.abs(cb[:, 0]) < 0.14) & (cb[:, 2] > 0.015)
ibody = 0
print('body slivers removed', sliver.sum())
Fb_out = Fb[~sliver]

# --- body tears under the collar (step 2d): enclosed holes in the jacket body (seen from above) are covered by a thin hidden patch,
#     1.2 mm UNDER the surrounding surface and overlapping it by 3 mm all round (closes the see-through, never shows above the jacket).
from scipy import ndimage as _ndi
def make_hole_patches(P_, Fb_, U0_, U1_):
    x0, x1, z0, z1 = -0.19, 0.19, -0.12, 0.09; Wg = int((x1-x0)*2000); Hg = int((z1-z0)*2000)
    sel_ = Fb_[(P_[Fb_][:, :, 1].min(1) > 1.30)]
    Hz_, _, hs_ = depthmap(P_[:, [0, 2, 1]]*[-1, 1, -1], sel_, (x0, x1, z0, z1), Wg, Hg)
    emp_ = ~np.isfinite(Hz_); lab_, n_ = _ndi.label(emp_); V_, T_, UA, UB = [], [], [], []
    vb_ = np.unique(Fb_.ravel())
    for k in range(1, n_+1):
        m = lab_ == k; a = m.sum()*(1000/hs_)**2; rr, cc = np.where(m)
        if a < 5 or a > 500 or rr.min() == 0 or cc.min() == 0 or rr.max() == Hg-1 or cc.max() == Wg-1: continue
        mg = int(0.003*hs_)+1; r0, r1, c0, c1 = rr.min()-mg, rr.max()+mg, cc.min()-mg, cc.max()+mg
        win = Hz_[r0:r1+1, c0:c1+1].copy(); hole = np.isnan(win) & m[r0:r1+1, c0:c1+1]
        known = np.isfinite(win); fill = np.where(known, win, np.nan)
        idx = _ndi.distance_transform_edt(~known, return_distances=False, return_indices=True); fill = win[idx[0], idx[1]]          # nearest known height
        for _ in range(200):                                                                                                       # relax the filled cells toward a smooth surface
            sm = (np.roll(fill, 1, 0)+np.roll(fill, -1, 0)+np.roll(fill, 1, 1)+np.roll(fill, -1, 1))/4; fill = np.where(known, fill, sm)
        low = _ndi.minimum_filter(fill, size=int(0.004*hs_)|1)-0.0012                                                              # always below the local surface
        st = max(2, int(0.001*hs_)); rs = np.arange(0, low.shape[0], st); cs = np.arange(0, low.shape[1], st)
        gx = x0+(c0+cs+.5)/hs_; gz = z1-(r0+rs+.5)/hs_
        Xg, Zg = np.meshgrid(gx, gz); Yg = low[np.ix_(rs, cs)]
        nr, nc = Xg.shape; Vk = np.c_[Xg.ravel(), Yg.ravel(), Zg.ravel()]; o = sum(len(v) for v in V_)
        Tk = []
        for i in range(nr-1):
            for j in range(nc-1):
                a_ = i*nc+j; b_ = a_+1; c_ = a_+nc; d_ = c_+1; Tk += [[a_, b_, c_], [b_, d_, c_]]       # CCW seen from +y (z increases with row index? checked below)
        Tk = np.array(Tk)+o
        nz = np.cross(Vk[Tk[:, 1]-o]-Vk[Tk[:, 0]-o], Vk[Tk[:, 2]-o]-Vk[Tk[:, 0]-o])[:, 1]
        if (nz < 0).mean() > 0.5: Tk = Tk[:, [0, 2, 1]]
        near = vb_[np.linalg.norm(P_[vb_][:, [0, 2]]-Vk[:, [0, 2]].mean(0), axis=1) < 0.03]; M_ = np.c_[P_[near], np.ones(len(near))]
        UA.append(np.c_[Vk, np.ones(len(Vk))]@np.linalg.lstsq(M_, U0_[near], rcond=None)[0]); UB.append(np.c_[Vk, np.ones(len(Vk))]@np.linalg.lstsq(M_, U1_[near], rcond=None)[0])
        V_.append(Vk); T_.append(Tk)
        print('HOLE PATCH: hole %.1f mm2 at x %.0f..%.0f z %.0f..%.0f mm -> patch %d x %d grid (%d tris), %.1f mm under the surface' % (
            a, (x0+cc.min()/hs_)*1000, (x0+cc.max()/hs_)*1000, (z1-rr.max()/hs_)*1000, (z1-rr.min()/hs_)*1000, nr, nc, len(Tk), 1.2))
    if not V_: return np.zeros((0, 3)), np.zeros((0, 3), int), np.zeros((0, 2)), np.zeros((0, 2))
    return np.vstack(V_), np.vstack(T_), np.vstack(UA), np.vstack(UB)
PATCH_V, PATCH_T, PATCH_U0, PATCH_U1 = make_hole_patches(P, Fb_out, U0, U1)
print('old lapel tris', lapel.sum(), 'collar tris kept', len(Fkeep), 'cut', len(Fcut))

# --- depth maps (front view): u=x, v=y, value = true z (frontmost)
BOX = (-0.20, 0.20, 1.08, 1.50); RES = 1000
W, H = int((BOX[1]-BOX[0])*RES), int((BOX[3]-BOX[2])*RES)
zbody, _, s = depthmap(P * [-1, 1, -1], Fb, BOX, W, H)
zbody = np.where(zbody > -0.02, zbody, -np.inf)           # front of the body only (not the back of the neck)
_g2, _b2, P2, _n2, _u0, _u1, Fs2 = load('/home/claude/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4.glb')
Fn = Fs2[[i for i, p in enumerate(_g2.meshes[1].primitives) if _g2.materials[p.material].name == 'Jacket_Lapel'][0]]
Tn = P2[Fn]; nn_ = np.cross(Tn[:, 1]-Tn[:, 0], Tn[:, 2]-Tn[:, 0]); nn_ /= np.linalg.norm(nn_, axis=1, keepdims=True)+1e-12
fr = (nn_[:, 2] > 0.3) & (Tn[:, :, 2].mean(1) > 0.02)
zlap, _, _ = depthmap(P2*[-1, 1, -1], Fn[fr], BOX, W, H)
def smooth_fill(z, sig):
    m = np.isfinite(z); z0 = np.where(m, z, 0.0)
    a = gaussian_filter(z0, sig); b = gaussian_filter(m.astype(float), sig)
    return a / np.maximum(b, 1e-9), b
zl_s, wl = smooth_fill(zlap, 6)
zl_s2, _ = smooth_fill(zlap, 25)
zl_s = np.where(wl > 0.05, zl_s, zl_s2)
zb_a, wba = smooth_fill(zbody, 3); zb_b, _ = smooth_fill(zbody, 20)
zb_s = np.where(wba > 0.3, zb_a, zb_b)                     # smooth chest surface, filled over small holes
def samp(img, x, y):
    c = np.clip(((x-BOX[0])*s-.5), 0, W-1.001); r = np.clip(((BOX[3]-y)*s-.5), 0, H-1.001)
    c0 = c.astype(int); r0 = r.astype(int); fc = c-c0; fr = r-r0
    return (img[r0, c0]*(1-fc)*(1-fr)+img[r0, c0+1]*fc*(1-fr)+img[r0+1, c0]*(1-fc)*fr+img[r0+1, c0+1]*fc*fr)
def body_z(x, y):
    ok = samp(np.isfinite(zbody).astype(float), x, y) > 0.999
    z = samp(np.where(np.isfinite(zbody), zbody, 0.0), x, y); return np.where(ok, z, np.nan)

# --- outline (|x|, y)
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
G_x = 0.063
Vpt = np.array([0.122, 1.394])     # notch: bottom of the V (end of the gorge line)
Tp = np.array([0.150, 1.410])      # peak tip (was 0.155, 1.422 = on the shoulder line)
CPd = 0.5; CPoff = 0.002           # collar point: half way up the peak edge, 2 mm off it
Nu, Nv = 64, 16
LIFT_TOP = 0.004                   # lapel height above the chest at the top (outer edge / peak)
def arc(Pc): d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Pc, axis=0), axis=1))]; return d/d[-1]
def resample(Pc, k):
    sa = arc(Pc); t = np.linspace(0, 1, k); return np.c_[np.interp(t, sa, Pc[:, 0]), np.interp(t, sa, Pc[:, 1])]
def vnorm(Pv, Tv):
    fn = np.cross(Pv[Tv[:, 1]]-Pv[Tv[:, 0]], Pv[Tv[:, 2]]-Pv[Tv[:, 0]]); nn = np.zeros_like(Pv)
    for k in range(3): np.add.at(nn, Tv[:, k], fn)
    ln = np.linalg.norm(nn, axis=1, keepdims=True); nn = np.where(ln > 1e-9, nn/np.maximum(ln, 1e-12), [0.0, 0.0, 1.0])
    return nn/np.linalg.norm(nn, axis=1, keepdims=True)
def grid_tris(nu, nv):
    T = []
    for i in range(nu):
        for j in range(nv):
            a = i*(nv+1)+j; b = a+1; c = a+nv+1; d = c+1
            T += [[a, c, b], [b, c, d]]
    return np.array(T)
def smoothstep(a, b, x): t = np.clip((x-a)/(b-a), 0, 1); return t*t*(3-2*t)

zc0 = -0.005
# obstacles for the collar: body only (neck/shoulder region), dense surface samples with outward normals
Vb = np.unique(Fb_out.ravel()); Vb = Vb[(P[Vb, 1] > 1.33)]
Fbr = Fb_out[(P[Fb_out][:, :, 1].mean(1) > 1.33) & (np.abs(P[Fb_out][:, :, 0].mean(1)) < 0.22)]
Tb = P[Fbr]; fnb = np.cross(Tb[:, 1]-Tb[:, 0], Tb[:, 2]-Tb[:, 0]); ab = np.linalg.norm(fnb, axis=1)
okb = ab > 1e-12; Tb = Tb[okb]; fnb = fnb[okb]/ab[okb, None]
ctr = Tb.mean(1); rr = np.c_[ctr[:, 0], np.zeros(len(ctr)), ctr[:, 2]+0.005]
rr[:, 1] = np.where(ctr[:, 1] > 1.43, 0.3*np.linalg.norm(rr, axis=1), 0)
fnb[(fnb*rr).sum(1) < 0] *= -1
SP, SN = [], []
for a in np.linspace(0, 1, 9):
    for b in np.linspace(0, 1-a, max(int(round((1-a)*8)), 0)+1):
        SP.append(Tb[:, 0]*(1-a-b)+Tb[:, 1]*a+Tb[:, 2]*b); SN.append(fnb)
SP = np.vstack(SP); SN = np.vstack(SN)
ObP = SP; ObN = SN; ObC = np.full(len(SP), 0.003)
tree = cKDTree(ObP); btree = cKDTree(SP)
def pushdir(Q):
    # chest (front): straight forward; neck/shoulder: outward from the neck and up
    rad = np.c_[Q[:, 0], np.zeros(len(Q)), Q[:, 2]-zc0]; rad /= np.linalg.norm(rad, axis=1, keepdims=True)+1e-12
    ru = rad + [0, 0.7, 0]; ru /= np.linalg.norm(ru, axis=1, keepdims=True)
    w = smoothstep(-0.01, 0.02, Q[:, 2])[:, None]
    dv = w*[0, 0, 1.0] + (1-w)*ru; return dv/np.linalg.norm(dv, axis=1, keepdims=True)
def push(Pts, mask, it=1):
    for _ in range(it):
        Q = Pts[mask]; dv = pushdir(Q)
        d, k = tree.query(Q, k=6)
        need = np.zeros(len(Q))
        for col in range(k.shape[1]):
            qp = ObP[k[:, col]]; n = ObN[k[:, col]]; c = ObC[k[:, col]]
            near = d[:, col] < 0.006
            dist = ((Q-qp)*n).sum(1)
            dn = np.maximum((dv*n).sum(1), 0.3)
            need = np.maximum(need, np.where(near & (dist < c), (c-dist)/dn, 0.0))
        Pts[mask] = Q + np.minimum(need, 0.004)[:, None]*dv
    return Pts

newP, newN, newU0, newU1, newT = [], [], [], [], []
base = len(P)
def emit(Pv, Tv, Nv_, c0, c1):
    o = base + sum(len(x) for x in newP)
    uvm = np.c_[Pv[:, 0], Pv[:, 1], Pv[:, 2], np.ones(len(Pv))]
    newP.append(Pv); newN.append(Nv_); newU0.append(uvm@c0); newU1.append(uvm@c1); newT.append(Tv+o)
def uvfit(idx):
    M = np.c_[P[idx], np.ones(len(idx))]
    return np.linalg.lstsq(M, U0[idx], rcond=None)[0], np.linalg.lstsq(M, U1[idx], rcond=None)[0]
def wall(E, drop_to, outward_xy_cen=None, flipref=None):
    k = len(E); Wt = np.vstack([E, drop_to]); WT = []
    for q in range(k-1): WT += [[q, q+1, k+q+1], [q, k+q+1, k+q]]
    return Wt, np.array(WT)
def orient(Wt, WT, refdir):
    wn = np.cross(Wt[WT[:, 1]]-Wt[WT[:, 0]], Wt[WT[:, 2]]-Wt[WT[:, 0]]); wc = Wt[WT].mean(1)
    fl = (wn*refdir(wc)).sum(1) < 0; WT = WT.copy(); WT[fl] = WT[fl][:, [0, 2, 1]]; return WT

report = []
D = {}
for side in (-1, 1):
    pi_ = body_opening(side)
    inner = lambda y: np.polyval(pi_, y)
    B0 = np.array([inner(B0y), B0y]); G = np.array([inner(Gy) if abs(inner(Gy)-G_x) < 0.01 else G_x, Gy])
    yA = np.linspace(B0y, Gy, 80); A = np.c_[inner(yA), yA]; A[-1] = G
    yB = np.linspace(1.14, 1.38, 50)
    B = np.vstack([B0, np.c_[np.polyval(po, yB), yB], [0.1445, 1.39], Tp])
    lGV = np.linalg.norm(Vpt-G); lVT = np.linalg.norm(Tp-Vpt)
    jV = int(round(Nv*lGV/(lGV+lVT)))
    top = np.vstack([G+(Vpt-G)*np.linspace(0, 1, jV+1)[:, None], Vpt+(Tp-Vpt)*np.linspace(0, 1, Nv-jV+1)[1:, None]])
    Au = resample(A, Nu+1); Bu = resample(B, Nu+1); Tv = top
    u = np.linspace(0, 1, Nu+1)[:, None, None]; v = np.linspace(0, 1, Nv+1)[None, :, None]
    Pg = (1-v)*Au[:, None, :]+v*Bu[:, None, :]+u*(Tv[None, :, :]-((1-v)*G+v*Tp))
    X = side*Pg[:, :, 0]; Y = Pg[:, :, 1]
    Z = samp(zl_s, X, Y)
    bz = body_z(X, Y)
    bz = np.where(bz > Z + 0.004, np.nan, bz)
    Z = np.where(np.isfinite(bz), np.maximum(Z, bz+0.003), Z)
    Z = gaussian_filter(Z, (1.5, 1.0), mode='nearest')
    # upper lapel: lie on the chest. cap height above smooth chest: LIFT_TOP at outer/top, more toward the roll line
    zc = samp(zb_s, X, Y)
    cap = LIFT_TOP + 0.006*(1-v[:, :, 0])**2
    wtop = smoothstep(1.29, 1.37, Y)
    zc = np.where(np.isfinite(bz), np.minimum(zc, bz), zc)
    Zc = np.minimum(Z, zc+cap)
    Z = (1-wtop)*Z + wtop*Zc
    Z = gaussian_filter(Z, (1.0, 1.0), mode='nearest')
    Z = (1-wtop)*Z + wtop*np.minimum(Z, zc+cap+0.001)
    Z = np.where(np.isfinite(bz), np.maximum(Z, bz+0.0025), Z)
    Pl = np.dstack([X, Y, Z]).reshape(-1, 3)
    T = grid_tris(Nu, Nv)
    nn = vnorm(Pl, T)
    if nn[:, 2].mean() < 0: T = T[:, [0, 2, 1]]; nn = -nn
    _fn = np.cross(Pl[T[:, 1]]-Pl[T[:, 0]], Pl[T[:, 2]]-Pl[T[:, 0]]); _fn /= np.linalg.norm(_fn, axis=1, keepdims=True)+1e-12; _c = Pl[T].mean(1)
    _st = np.abs(_fn[:, 1]) > 0.8
    print('STEEP lapel-grid tris side %d: %d with |n_y|>0.8 ; sample centroids mm %s' % (side, _st.sum(), np.round(_c[_st][:6]*1000, 0).tolist()))
    lv = np.unique(Fp[lapel].ravel()); lv = lv[np.sign(P[lv, 0]) == side]
    M = np.c_[P[lv, 0], P[lv, 1], np.ones(len(lv))]
    c0 = np.linalg.lstsq(M, U0[lv], rcond=None)[0]; c1 = np.linalg.lstsq(M, U1[lv], rcond=None)[0]
    c0 = np.vstack([c0[:2], [0, 0], c0[2:]]); c1 = np.vstack([c1[:2], [0, 0], c1[2:]])
    # lapel edge walls: inner edge (6 mm), outer edge + peak edge (down to the chest, max 8 mm); none along the gorge
    idx = lambda i, j: i*(Nv+1)+j
    loop = [idx(i, 0) for i in range(Nu+1)] + [idx(Nu, j) for j in range(jV, Nv+1)] + [idx(i, Nv) for i in range(Nu-1, -1, -1)]
    lim = np.full(len(loop), 0.008); lim[:Nu+1] = 0.006
    E = Pl[loop].copy(); eb = body_z(E[:, 0], E[:, 1]); eb = np.where(eb > E[:, 2] + 0.002, np.nan, eb)
    drop = np.where(np.isfinite(eb) & (eb < E[:, 2]), np.minimum(eb-0.001, E[:, 2]-0.002), E[:, 2]-0.004)
    drop = np.maximum(drop, E[:, 2]-lim)
    # split the loop where it jumps from inner edge top (G) to V (gorge has no wall)
    segs = [list(range(0, Nu+1)), list(range(Nu+1, len(loop)))]
    cen = Pl[:, :2].mean(0)
    emit(Pl, T, nn, c0, c1)
    for sg in segs:
        Wt, WT = wall(E[sg], np.c_[E[sg, :2], drop[sg]])
        WT = orient(Wt, WT, lambda wc: np.c_[wc[:, :2]-cen, np.zeros(len(wc))])
        emit(Wt, WT, vnorm(Wt, WT), c0, c1)
    gap = (Z-bz)*1000
    report.append('side %d lapel: height above chest mm  top rows max %.1f, peak tip %.1f, whole max %.1f; tip at y %.3f' % (
        side, np.nanmax(gap[-6:]), gap[-1, -1] if np.isfinite(gap[-1, -1]) else -1, np.nanmax(gap), Y[-1, -1]))
    # ---------------- collar front band ----------------
    gorge = Pl.reshape(Nu+1, Nv+1, 3)[Nu, :jV+1]          # exact lapel top points G..V
    Gp = gorge[0]; Vp = gorge[-1]
    TpP = Pl.reshape(Nu+1, Nv+1, 3)[Nu, Nv]
    d2 = (Tp-Vpt)/np.linalg.norm(Tp-Vpt); perp = np.array([-d2[1], d2[0]])   # toward the collar side (up/in)
    cp2 = Vpt + CPd*(Tp-Vpt) + CPoff*perp
    cpz = samp(zb_s, side*cp2[0], cp2[1]) + 0.004
    CP = np.array([side*cp2[0], cp2[1], cpz])
    # collar section where the new band starts (overlaps 10 mm over the kept collar)
    D[side] = dict(gorge=gorge.copy(), Gp=Gp.copy(), Vp=Vp.copy(), CP=CP.copy()); print('ANCHORS side %d G %s V %s CP %s' % (side, np.round(Gp*1000,1), np.round(Vp*1000,1), np.round(CP*1000,1)))

# ======================= ONE-PIECE COLLAR =======================
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter
# (1) top-view height map of the body: x,z -> highest body y
sel = Fb_out[(P[Fb_out][:, :, 1].min(1) > 1.25) & (np.abs(P[Fb_out][:, :, 0]).max(1) < 0.25) & (np.abs(P[Fb_out][:, :, 2]).max(1) < 0.16)]
HB = (-0.25, 0.25, -0.16, 0.16); HS = 1000
Hz, _, hs = depthmap(P[:, [0, 2, 1]]*[-1, 1, -1], sel, HB, int((HB[1]-HB[0])*HS), int((HB[3]-HB[2])*HS))
def hfield(x, z):
    c = np.clip(np.round((x-HB[0])*hs-.5).astype(int), 0, Hz.shape[1]-1); r = np.clip(np.round((HB[3]-z)*hs-.5).astype(int), 0, Hz.shape[0]-1)
    return Hz[r, c]
def pol(Pt): return np.degrees(np.arctan2(Pt[0], -(Pt[2]-zc0))), np.hypot(Pt[0], Pt[2]-zc0)
def solve_r(phi, ytar):
    rg = np.arange(0.072, 0.22, 0.0005); ph = np.radians(phi)
    h = hfield(rg*np.sin(ph), zc0-rg*np.cos(ph)); ok = np.isfinite(h) & (h <= ytar)
    return rg[np.argmax(ok)] if ok.any() else np.nan
# (2) fold curve (top edge, neck side) and fall curve (lower edge, lies on the body), both as |phi| -> (r, y), per side
FOLD_K = [(0, 0.073, 1.488), (40, 0.074, 1.485), (70, 0.075, 1.476), (100, 0.075, 1.462)]   # phi deg, r, y
FALL_R = [(0, 0.0865), (35, 0.0860), (65, 0.097), (90, 0.110)]    # lower-edge plan radius (m) at phi deg; height comes from the body
BULGE = 0.004                                   # outward roll of the collar sheet between fold and fall (m)
curves = {}
for side in (-1, 1):
    d = D[side]; pG, rG = pol(d['Gp']); pC, rC = pol(d['CP'])
    pG, pC = abs(pG), abs(pC)
    fk = [k for k in FOLD_K if k[0] < pG-12] + [(pG, rG, d['Gp'][1])]
    fr = PchipInterpolator([k[0] for k in fk], [k[1] for k in fk]); fy = PchipInterpolator([k[0] for k in fk], [k[2] for k in fk])
    # lower edge: smooth plan-view curve r(phi); its height = body surface + 2 mm (so it rides the body, no kink, little pulling needed)
    kk = [(a, r) for a, r in FALL_R if a < pC-12]
    lr = PchipInterpolator([a for a, _ in kk]+[pC], [r for _, r in kk]+[rC])
    ph_ = np.linspace(0, pC, 241); r_ = lr(ph_); a_ = np.radians(ph_)
    h_ = hfield(r_*np.sin(a_), zc0-r_*np.cos(a_))+0.002; bad = ~np.isfinite(h_) | (h_ < 1.30)
    h_ = np.interp(ph_, ph_[~bad], h_[~bad]); h_[-1] = d['CP'][1]
    h_ = gaussian_filter(np.r_[[h_[0]]*12, h_, [h_[-1]]*12], 4)[12:-12]; h_[-1] = d['CP'][1]
    ly = (lambda ph_=ph_, h_=h_: (lambda x: np.interp(x, ph_, h_)))()
    lk = [(a, float(lr(a)), float(ly(a))) for a in (0, 35, 65, 90)] + [(pC, rC, d['CP'][1])]
    curves[side] = dict(pG=pG, pC=pC, fr=fr, fy=fy, lr=lr, ly=ly)
    print('side %d: gorge start phi %.1f r %.1f mm y %.1f | collar point phi %.1f r %.1f mm y %.1f | fold keys %s | fall keys %s' % (
        side, pG, rG*1000, d['Gp'][1]*1000, pC, rC*1000, d['CP'][1]*1000, [(a, round(r*1000, 1), round(y*1000, 1)) for a, r, y in fk],
        [(a, round(r*1000, 1), round(y*1000, 1)) for a, r, y in lk]))
Mu = 72
Mv = jV+6
ut = np.linspace(0, 1, Mu+1)
def crease_report(Cp_, tag):
    G_ = Cp_.reshape(Mu+1, Mv+1, 3)
    n_ = np.cross(G_[1:, 1:]-G_[:-1, :-1], G_[:-1, 1:]-G_[1:, :-1]); n_ /= np.linalg.norm(n_, axis=2, keepdims=True)+1e-12     # (Mu, Mv, 3) cell normals
    au = np.degrees(np.arccos(np.clip((n_[1:]*n_[:-1]).sum(2), -1, 1))); av = np.degrees(np.arccos(np.clip((n_[:, 1:]*n_[:, :-1]).sum(2), -1, 1)))
    out = []
    for nm, a_, di, dj in (('along', au, 1, 0), ('across', av, 0, 1)):
        for k in np.argsort(a_.ravel())[::-1][:6]:
            i, j = np.unravel_index(k, a_.shape); q = G_[i+di, j+dj]
            out.append((a_[i, j], nm, i, j, q))
    out.sort(key=lambda t: -t[0])
    print('CREASES %s: cells>25deg along %d across %d (of %d)' % (tag, (au > 25).sum(), (av > 25).sum(), au.size))
    for a_, nm, i, j, q in out[:8]: print('   %5.1f deg %-6s u%2d v%2d at mm %s' % (a_, nm, i, j, np.round(q*1000, 1)))
PHS = 88.0                                       # back section: plain loft between fold and fall for |phi| < PHS; front ends: Coons patches (shared boundary column)
Mf = 16; Mb = Mu-2*Mf
def pt_at(side, key_r, key_y, ph_abs):
    ph_abs = np.asarray(ph_abs, float); r_ = curves[side][key_r](ph_abs); y_ = curves[side][key_y](ph_abs); ph = np.radians(side*ph_abs)
    return np.c_[r_*np.sin(ph), y_, zc0-r_*np.cos(ph)]
def endcurve(d):
    return np.vstack([d['gorge'], d['Vp']+(d['CP']-d['Vp'])*np.linspace(0, 1, Mv-jV+1)[1:, None]])
tv = np.linspace(0, 1, Mv+1)[:, None]
cols = [None]*(Mu+1)
# --- back loft
phb = np.linspace(-PHS, PHS, Mb+1)
for k, ph in enumerate(phb):
    sd = -1 if ph < 0 else 1; a_ = abs(ph)
    Fp_ = pt_at(sd, 'fr', 'fy', a_)[0]; Lp_ = pt_at(sd, 'lr', 'ly', a_)[0]
    roll = BULGE*smoothstep(PHS, PHS-30, a_)
    radial = np.array([Fp_[0]+Lp_[0], 0, Fp_[2]+Lp_[2]-2*zc0]); radial /= np.linalg.norm(radial)
    cols[Mf+k] = (1-tv)*Fp_+tv*Lp_+(roll*np.sin(np.pi*tv))*radial
# --- front Coons patches (left: side -1, columns 0..Mf, end curve at column 0; right: side +1, columns Mu-Mf..Mu, end curve at column Mu)
for sd, idxs in ((-1, list(range(0, Mf+1))), (1, list(range(Mu, Mu-Mf-1, -1)))):
    d = D[sd]; E = endcurve(d); pG_ = curves[sd]['pG']; pC_ = curves[sd]['pC']
    Fs_ = pt_at(sd, 'fr', 'fy', PHS)[0]; Ls_ = pt_at(sd, 'lr', 'ly', PHS)[0]; B = (1-tv)*Fs_+tv*Ls_
    for q, ci in enumerate(idxs):
        u_ = q/Mf
        Fq = pt_at(sd, 'fr', 'fy', pG_+(PHS-pG_)*u_)[0]; Lq = pt_at(sd, 'lr', 'ly', pC_+(PHS-pC_)*u_)[0]
        if q == 0: Fq, Lq = E[0], E[-1]
        S_ = (1-tv)*Fq+tv*Lq+(1-u_)*E+u_*B-((1-u_)*(1-tv)*E[0]+(1-u_)*tv*E[-1]+u_*(1-tv)*Fs_+u_*tv*Ls_)
        if ci != Mf and ci != Mu-Mf: cols[ci] = S_
Cg = np.stack(cols, axis=0)                      # (Mu+1, Mv+1, 3)
Cp = Cg.reshape(-1, 3)
crease_report(Cp, '0 raw Coons+roll')
bm = np.zeros((Mu+1, Mv+1), bool); bm[0, :] = bm[-1, :] = bm[:, 0] = bm[:, -1] = True
fixed = np.zeros((Mu+1, Mv+1), bool); fixed[0, :] = fixed[Mu, :] = True; fixed = fixed.ravel()                  # both front end curves stay exactly on the gorge/peak edge
fallm = np.zeros((Mu+1, Mv+1), bool); fallm[1:Mu, Mv] = True; fallm = fallm.ravel()
for it in range(60):
    Cp = push(Cp, ~fixed & ~fallm)
    dB, kB = btree.query(Cp[fallm]); nB = SN[kB]
    dist = ((Cp[fallm]-SP[kB])*nB).sum(1)
    dvf = pushdir(Cp[fallm]); dn = np.maximum((dvf*nB).sum(1), 0.3)
    Cp[fallm] -= ((dist-0.002)/dn)[:, None]*dvf*0.5
    Cg = Cp.reshape(Mu+1, Mv+1, 3)
    L = Cg.copy()
    L[1:-1, 1:-1] = 0.25*(Cg[:-2, 1:-1]+Cg[2:, 1:-1]+Cg[1:-1, :-2]+Cg[1:-1, 2:])
    L[1:-1, Mv] = 0.5*(Cg[:-2, Mv]+Cg[2:, Mv]); L[1:-1, 0] = 0.5*(Cg[:-2, 0]+Cg[2:, 0])
    sm = ~bm.copy(); sm[1:-1, Mv] = True; sm[1:-1, 0] = True
    Cg = np.where(sm[:, :, None], 0.5*Cg+0.5*L, Cg)
    Cp = Cg.reshape(-1, 3)
crease_report(Cp, '1 after iterations')
Cg = Cp.reshape(Mu+1, Mv+1, 3)
for j in range(Mv-3, Mv):                       # last rows: blend between the row 4 steps in and the lower edge so nothing can fold over
    t_ = (j-(Mv-4))/4.0; Cg[1:Mu, j] = (1-t_)*Cg[1:Mu, Mv-4]+t_*Cg[1:Mu, Mv]
Cp = Cg.reshape(-1, 3)
def pen_report(Cp_, tag):
    h = hfield(Cp_[:, 0], Cp_[:, 2]); ok = np.isfinite(h) & (h > 1.30); dep = np.where(ok, h-Cp_[:, 1], 0)
    print('PENETRATION %s: %d of %d collar verts below the body top surface (max %.1f mm)' % (tag, (dep > 0.0005).sum(), len(Cp_), dep.max()*1000))
crease_report(Cp, '2 after row blend'); pen_report(Cp, '2')
lastrows = np.zeros((Mu+1, Mv+1), bool); lastrows[:, Mv-4:] = True
Cp = push(Cp, ~fixed & ~fallm & ~lastrows.ravel(), it=3)
crease_report(Cp, '3 after final push (rows away from the lower edge only)'); pen_report(Cp, '3')
CT = grid_tris(Mu, Mv); cn = vnorm(Cp, CT)
if ((cn*np.c_[Cp[:, 0], np.zeros(len(Cp)), Cp[:, 2]-zc0]).sum(1)).mean() < 0: CT = CT[:, [0, 2, 1]]; cn = -cn
# UV: own clean mapping for the collar (old collar UVs are island-by-island and cannot be fitted). Scale/direction/offset are measured from the
# two big lapel pieces (signed-x affine fits, rms ~0.03 unit): weave U1 = planar in x (33.8/m), V1 = planar in y (-33.5/m). On the collar the
# same numbers are applied to the DISTANCE ALONG the collar from centre back (signed) and to a height-like coordinate (distance across the band
# from the fold, measured down from the fold height at centre back), so there is no smearing at the sides of the neck and no break at the back.
fit_ = {}
for sd in (-1, 1):
    vv = np.unique(Fp[lapel & (np.sign(P[Fp][:, :, 0].mean(1)) == sd)].ravel()); Mq = np.c_[P[vv, 0], P[vv, 1], np.ones(len(vv))]
    fit_[sd] = (np.linalg.lstsq(Mq, U0[vv], rcond=None)[0], np.linalg.lstsq(Mq, U1[vv], rcond=None)[0])
cL0, cL1 = fit_[-1]; cR0, cR1 = fit_[1]
print('lapel UV: U1 dU/dx L %.2f R %.2f, dV/dy L %.2f R %.2f' % (cL1[0, 0], cR1[0, 0], cL1[1, 1], cR1[1, 1]))
Cg3 = Cp.reshape(Mu+1, Mv+1, 3)
jm = Mv//2
seg = np.linalg.norm(np.diff(Cg3[:, jm], axis=0), axis=1); su = np.r_[0, np.cumsum(seg)]; su = su-su[Mu//2]                 # signed distance from centre back (x<0 = left)
sv = np.r_[np.zeros((1, Mu+1)), np.cumsum(np.linalg.norm(np.diff(Cg3, axis=1), axis=2).T, axis=0)].T                          # (Mu+1, Mv+1) from fold edge
xs_signed = np.repeat(su[:, None], Mv+1, axis=1); yy = Cg3[Mu//2, 0, 1]-sv
x_ = xs_signed.ravel(); y_ = yy.ravel(); xa = np.abs(x_)
# weave (U1): same global convention both sides -> average of the two fits, signed x
cuv1 = np.c_[x_, y_, np.ones(len(x_))]@((cL1+cR1)/2)
# atlas (U0): left/right pieces mirror each other (gradient in x flips) -> use |x| with averaged gradients/offsets so both halves match
g0x = (-cL0[0]+cR0[0])/2; g0y = (cL0[1]+cR0[1])/2; o0 = (cL0[2]+cR0[2])/2
cuv0 = xa[:, None]*g0x[None, :]+y_[:, None]*g0y[None, :]+o0[None, :]
o_ = base + sum(len(x_) for x_ in newP)
newP.append(Cp); newN.append(cn); newU0.append(cuv0); newU1.append(cuv1); newT.append(CT+o_)
cc0 = np.linalg.lstsq(np.c_[Cp, np.ones(len(Cp))], cuv0, rcond=None)[0]; cc1 = np.linalg.lstsq(np.c_[Cp, np.ones(len(Cp))], cuv1, rcond=None)[0]   # (walls only: approx. same UV)
# small walls under the lower edge and the two V..collar-point ends (max 8 mm), down toward the body
Cg = Cp.reshape(Mu+1, Mv+1, 3)
edge = np.vstack([Cg[0, jV:Mv+1], Cg[1:Mu, Mv], Cg[Mu, Mv:jV-1:-1]])
d, k = btree.query(edge); n = SN[k]
dist = ((edge-SP[k])*n).sum(1); dd = np.clip(dist+0.0012, 0, 0.010)          # sink the wall 1.2 mm into the body so no see-through slit remains
Wt, WT = wall(edge, edge-(dd/np.maximum((pushdir(edge)*n).sum(1), 0.3))[:, None]*pushdir(edge))
ccen = Cp.mean(0); WT = orient(Wt, WT, lambda wc: wc-ccen)
emit(Wt, WT, vnorm(Wt, WT), cc0, cc1)
dBk, _ = cKDTree(SP).query(Cp)
report.append('collar: ONE grid %d x %d (%d tris), closest approach to body %.1f mm, fold top y %.1f mm at back, lower edge y %.1f mm at back' % (
    Mu, Mv, len(CT), dBk.min()*1000, Cg[Mu//2, 0, 1]*1000, Cg[Mu//2, Mv, 1]*1000))

Cg_ = Cp.reshape(Mu+1, Mv+1, 3)
for ci in (0, 1, 2, 3, 5, 8):
    q = Cg_[ci, jV:Mv+1]; bzv = body_z(q[:, 0], q[:, 1])
    print('FRONT-END col %d (V..CP): clearance above chest mm %s | y mm %s' % (ci, np.round((q[:, 2]-bzv)*1000, 1), np.round(q[:, 1]*1000, 0)))
for ci in (0, 1, 2, 4):
    q = Cg_[ci, 0:jV+1]; bzv = body_z(q[:, 0], q[:, 1])
    print('GORGE-ROWS col %d (G..V): x %s | y %s | z %s | clear %s' % (ci, np.round(q[:, 0]*1000, 0), np.round(q[:, 1]*1000, 0), np.round(q[:, 2]*1000, 0), np.round((q[:, 2]-bzv)*1000, 1)))
_G = Cp.reshape(Mu+1, Mv+1, 3); _n = np.cross(_G[1:, 1:]-_G[:-1, :-1], _G[:-1, 1:]-_G[1:, :-1]); _n /= np.linalg.norm(_n, axis=2, keepdims=True)+1e-12
_cc = (_G[1:, 1:]+_G[:-1, :-1])/2; _s = np.abs(_n[:, :, 1]) > 0.8
for nm, sl in (('left front', slice(0, 8)), ('right front', slice(Mu-8, Mu))):
    ii, jj = np.where(_s[sl]); ii = ii+(sl.start or 0)
    print('STEEP collar cells %s: %d  e.g. (u,v,x,y,z mm) %s' % (nm, len(ii), [(int(a), int(b), *np.round(_cc[a, b]*1000, 0).tolist()) for a, b in list(zip(ii, jj))[:8]]))
if len(PATCH_V):
    o_ = base+sum(len(x_) for x_ in newP)
    newP.append(PATCH_V); newN.append(np.tile([0.0, 1.0, 0.0], (len(PATCH_V), 1))); newU0.append(PATCH_U0); newU1.append(PATCH_U1)
    Fb_out = np.vstack([Fb_out, PATCH_T+o_])
newP = np.vstack(newP); Fnew = np.vstack(newT)
PP = np.vstack([P, newP]); NN = np.vstack([N, np.vstack(newN)]); UU0 = np.vstack([U0, np.vstack(newU0)]); UU1 = np.vstack([U1, np.vstack(newU1)])
Fpk = Fnew                                       # lapels + walls + the ONE collar. No old collar triangles at all.
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
pr[ibody].indices = addacc(Fb_out.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
pr[ipk].indices = addacc(Fpk.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
print('\n'.join(report))
print('new verts', len(newP), 'peak tris', len(Fpk), 'saved', dst)
