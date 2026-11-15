# Repair step 2b: peak lapel collar join + peak tips (Jacket_Lapel_Peak, both sides).
# Input : MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb   (not modified)
# Output: new file given as argv[2]
# Same as peak_step2.py (lapel outline, inner edge, button point unchanged) plus:
# - lapel top edge = one straight gorge line from the neck (G) to the notch (V), then the peak edge V -> tip
# - peak tip lowered onto the chest, below the shoulder line
# - upper lapel lies on the chest (~4 mm, blended into the unchanged lower lapel) -> short edge walls only
# - ragged front ends of the peak collar removed and rebuilt as one clean band per side whose lower edge
#   is exactly the lapel gorge line; collar point sits next to the peak edge (tight V)
import sys, collections
import numpy as np
sys.path.insert(0, '/Users/mannywest/Projects/mw-suit/scripts/check'); sys.path.insert(0, '/Users/mannywest/Projects/mw-suit/scripts')
from common import load, depthmap
from pygltflib import Accessor, BufferView
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

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
print('old lapel tris', lapel.sum(), 'collar tris kept', len(Fkeep), 'cut', len(Fcut))

# --- depth maps (front view): u=x, v=y, value = true z (frontmost)
BOX = (-0.20, 0.20, 1.08, 1.50); RES = 1000
W, H = int((BOX[1]-BOX[0])*RES), int((BOX[3]-BOX[2])*RES)
zbody, _, s = depthmap(P * [-1, 1, -1], Fb, BOX, W, H)
zbody = np.where(zbody > -0.02, zbody, -np.inf)           # front of the body only (not the back of the neck)
_g2, _b2, P2, _n2, _u0, _u1, Fs2 = load('/Users/mannywest/Projects/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4.glb')
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
# obstacles for the collar band: body (neck/shoulder region) + kept collar, with outward normals
Vb = np.unique(Fb_out.ravel()); Vb = Vb[(P[Vb, 1] > 1.33)]
Vk = np.unique(Fkeep.ravel())
def outward(idx):
    n = N[idx].copy(); r = np.c_[P[idx, 0], np.zeros(len(idx)), P[idx, 2]+0.005]
    r[:, 1] = np.where(P[idx, 1] > 1.43, 0.3*np.linalg.norm(r, axis=1), 0)   # top of shoulder: also upward
    fl = (n*r).sum(1) < 0; n[fl] *= -1; return n
# dense samples of the body surface (every ~2 mm) with face normals, plus kept collar vertices
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
Fkr = Fkeep[P[Fkeep][:, :, 2].mean(1) > -0.09]
Tk = P[Fkr]; fnk = np.cross(Tk[:, 1]-Tk[:, 0], Tk[:, 2]-Tk[:, 0]); ak = np.linalg.norm(fnk, axis=1)
okk = ak > 1e-12; Tk = Tk[okk]; fnk = fnk[okk]/ak[okk, None]
ck = Tk.mean(1); fnk[(fnk*np.c_[ck[:, 0], np.zeros(len(ck)), ck[:, 2]+0.005]).sum(1) < 0] *= -1
KP, KN = [], []
for a in np.linspace(0, 1, 9):
    for b in np.linspace(0, 1-a, max(int(round((1-a)*8)), 0)+1):
        KP.append(Tk[:, 0]*(1-a-b)+Tk[:, 1]*a+Tk[:, 2]*b); KN.append(fnk)
KP = np.vstack(KP); KN = np.vstack(KN)
ObP = np.vstack([SP, KP]); ObN = np.vstack([SN, KN]); ObC = np.r_[np.full(len(SP), 0.003), np.full(len(KP), 0.0015)]
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
    kv = Vk[(np.sign(P[Vk, 0]) == side) & (np.abs(P[Vk, 2]-(ZC-0.012)) < 0.004)]
    T0 = P[kv[np.argmax(P[kv, 1])]].copy(); L0 = P[kv[np.argmin(P[kv, 1])]].copy()
    def cyl(a, b, t, ease=True):
        ra = np.hypot(a[0], a[2]-zc0); rb = np.hypot(b[0], b[2]-zc0)
        ta = np.arctan2(a[2]-zc0, abs(a[0])); tb = np.arctan2(b[2]-zc0, abs(b[0]))
        th = ta+(tb-ta)*t; r = ra+(rb-ra)*t; e = t*t*(3-2*t) if ease else t
        y = a[1]+(b[1]-a[1])*e
        return np.c_[side*r*np.cos(th), y, zc0+r*np.sin(th)]
    Mu = 28; Mv = jV + 4
    t = np.linspace(0, 1, Mu+1)
    fold = cyl(T0, Gp, t)                                  # v=0: roll/fold line, joins the lapel roll line at G
    fall = cyl(L0, CP, t, ease=False)                      # v=1: outer edge of the collar to the collar point
    endc = np.vstack([gorge, Vp+(CP-Vp)*np.linspace(0, 1, Mv-jV+1)[1:, None]])   # u=1: gorge G..V then V..CP
    back = T0+(L0-T0)*np.linspace(0, 1, Mv+1)[:, None]    # u=0
    # rescale end/back params so v matches arc-length on the end curve
    U = t[:, None, None]; Vv = np.linspace(0, 1, Mv+1)[None, :, None]
    sv = arc(endc[:, :2])[None, :, None]
    Cg = ((1-Vv)*fold[:, None, :]+Vv*fall[:, None, :] + (1-U)*back[None, :, :]+U*endc[None, :, :]
          - ((1-U)*(1-Vv)*T0+(1-U)*Vv*L0+U*(1-Vv)*Gp+U*Vv*CP))
    Cp = Cg.reshape(-1, 3)
    fixed = np.zeros((Mu+1, Mv+1), bool); fixed[Mu, :jV+1] = True; fixed = fixed.ravel()
    bnd = np.zeros((Mu+1, Mv+1), bool); bnd[0, :] = bnd[-1, :] = bnd[:, 0] = bnd[:, -1] = True; bnd = bnd.ravel()
    # lie on the chest near the front (front-view height), then push clear of body/kept collar, smooth interior
    fallm = np.zeros((Mu+1, Mv+1), bool); fallm[:Mu, Mv] = True; fallm = fallm.ravel()
    bm = bnd.reshape(Mu+1, Mv+1)
    for it in range(60):
        Cp = push(Cp, ~fixed & ~fallm)
        # outer edge of the collar lies down on the shoulder/chest (2 mm above the body)
        dB, kB = btree.query(Cp[fallm]); nB = SN[kB]
        dist = ((Cp[fallm]-SP[kB])*nB).sum(1)
        dvf = pushdir(Cp[fallm]); dn = np.maximum((dvf*nB).sum(1), 0.3)
        Cp[fallm] -= ((dist-0.002)/dn)[:, None]*dvf*0.5
        Cg = Cp.reshape(Mu+1, Mv+1, 3)
        L = Cg.copy()
        L[1:-1, 1:-1] = 0.25*(Cg[:-2, 1:-1]+Cg[2:, 1:-1]+Cg[1:-1, :-2]+Cg[1:-1, 2:])
        L[1:-1, Mv] = 0.5*(Cg[:-2, Mv]+Cg[2:, Mv])          # outer edge: smooth along its length
        L[1:-1, 0] = 0.5*(Cg[:-2, 0]+Cg[2:, 0])              # fold edge: smooth along its length
        sm = ~bm.copy(); sm[1:-1, Mv] = True; sm[1:-1, 0] = True
        Cg = np.where(sm[:, :, None], 0.5*Cg+0.5*L, Cg)
        Cp = Cg.reshape(-1, 3)
    Cp = push(Cp, ~fixed & ~fallm, it=3)
    CT = grid_tris(Mu, Mv)
    cn = vnorm(Cp, CT)
    if ((cn*np.c_[Cp[:, 0], np.zeros(len(Cp)), Cp[:, 2]-zc0]).sum(1)).mean() < 0: CT = CT[:, [0, 2, 1]]; cn = -cn
    cut_v = np.unique(Fcut.ravel()); cut_v = cut_v[np.sign(P[cut_v, 0]) == side]
    cc0, cc1 = uvfit(cut_v)
    emit(Cp, CT, cn, cc0, cc1)
    # small walls under the collar outer edge and collar end, down toward the body (max 5 mm)
    Cg = Cp.reshape(Mu+1, Mv+1, 3)
    edge = np.vstack([Cg[:, Mv], Cg[Mu, Mv-1:jV-1:-1]])
    d, k = btree.query(edge); n = SN[k]
    dist = ((edge-SP[k])*n).sum(1); dd = np.clip(dist-0.0005, 0, 0.008)
    Wt, WT = wall(edge, edge-(dd/np.maximum((pushdir(edge)*n).sum(1), 0.3))[:, None]*pushdir(edge))
    ccen = Cp.mean(0)
    WT = orient(Wt, WT, lambda wc: wc-ccen)
    emit(Wt, WT, vnorm(Wt, WT), cc0, cc1)
    # report: clearance of the collar band above the body
    dB, kB = cKDTree(P[Vb]).query(Cp)
    report.append('side %d collar band: %d tris, collar point %s mm, fold start %s, fall start %s' % (
        side, len(CT), np.round(CP*1000, 1), np.round(T0*1000, 1), np.round(L0*1000, 1)))

newP = np.vstack(newP); Fnew = np.vstack(newT)
PP = np.vstack([P, newP]); NN = np.vstack([N, np.vstack(newN)]); UU0 = np.vstack([U0, np.vstack(newU0)]); UU1 = np.vstack([U1, np.vstack(newU1)])
Fpk = np.vstack([Fnew, Fkeep])
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
