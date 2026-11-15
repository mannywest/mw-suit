# Shawl lapel step 1: ONE continuous shawl collar+lapel band on the BASE jacket (body only).
# Input : MW_Tailleur_suit_v4_BASE_stepC_neck.glb   (not modified)
# Output: new GLB (argv[2]).  Lapel UV fits are taken from the peak step2d file (argv[3], default repo copy).
# Per side one band from the button point (tip) up the front edge, round the neck, to the centre back. Inner/fold edge I(s) = front edge, then fold curve
# round the neck. Outer/fall edge O(s) = smooth outer sweep, then the fall curve riding the shoulder. No gorge seam: ONE grid (both sides share the
# centre-back column). Shape: Coons blend + push/relax against the body (same method as peak_step2c).
import sys, collections
import numpy as np
sys.path.insert(0, '/home/claude/work/scripts/check'); sys.path.insert(0, '/home/claude/work/scripts')
from common import load, depthmap
from pygltflib import Accessor, BufferView, Primitive, Attributes
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.spatial import cKDTree
from scipy.interpolate import PchipInterpolator
import copy

src, dst = sys.argv[1], sys.argv[2]
UVSRC = sys.argv[3] if len(sys.argv) > 3 else '/home/claude/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_peak_step2d_shoulders.glb'
g, blob, P, N, U0, U1, Fs = load(src)
pr = g.meshes[1].primitives
Fb = Fs[0]
zc0 = -0.005
B0y = 1.115                       # button point / tip height (same as the peak lapel bottom)
LIFT_IN, LIFT_OUT = 0.004, 0.0025
BULGE = 0.004
NS1, NS2, Mv = 70, 44, 16
NS = NS1 + NS2; Mu = 2 * NS

# ------------------------------------------------------------------ UV fits from the existing lapel (same weave/atlas convention)
g2, b2, P2, N2, V0, V1, Fs2 = load(UVSRC)
ip2 = [i for i, p in enumerate(g2.meshes[1].primitives) if g2.materials[p.material].name == 'Jacket_Lapel_Peak'][0]
vv = np.unique(Fs2[ip2].ravel()); vv = vv[(P2[vv, 1] > 1.13) & (P2[vv, 1] < 1.37) & (np.abs(P2[vv, 0]) > 0.03)]
fit = {}
for sd in (-1, 1):
    q = vv[np.sign(P2[vv, 0]) == sd]; M = np.c_[P2[q, 0], P2[q, 1], np.ones(len(q))]
    c0 = np.linalg.lstsq(M, V0[q], rcond=None)[0]; c1 = np.linalg.lstsq(M, V1[q], rcond=None)[0]
    print('UV fit side %d: n %d rms U0 %.4f U1 %.4f' % (sd, len(q), np.sqrt(((M@c0-V0[q])**2).mean()), np.sqrt(((M@c1-V1[q])**2).mean())))
    fit[sd] = (c0, c1)

# ------------------------------------------------------------------ body depth maps (front) and top height field
BOX = (-0.20, 0.20, 1.08, 1.50); RES = 1000
W, H = int((BOX[1]-BOX[0])*RES), int((BOX[3]-BOX[2])*RES)
zbody, _, s = depthmap(P * [-1, 1, -1], Fb, BOX, W, H)
zbody = np.where(zbody > -0.02, zbody, -np.inf)
def smooth_fill(z, sig):
    m = np.isfinite(z); z0 = np.where(m, z, 0.0)
    a = gaussian_filter(z0, sig); b = gaussian_filter(m.astype(float), sig)
    return a / np.maximum(b, 1e-9), b
zb_a, wba = smooth_fill(zbody, 3); zb_b, _ = smooth_fill(zbody, 20)
zb_s = np.where(wba > 0.3, zb_a, zb_b)
def samp(img, x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    c = np.clip(((x-BOX[0])*s-.5), 0, W-1.001); r = np.clip(((BOX[3]-y)*s-.5), 0, H-1.001)
    c0 = c.astype(int); r0 = r.astype(int); fc = c-c0; fr = r-r0
    return (img[r0, c0]*(1-fc)*(1-fr)+img[r0, c0+1]*fc*(1-fr)+img[r0+1, c0]*(1-fc)*fr+img[r0+1, c0+1]*fc*fr)
from scipy.ndimage import median_filter as _med
zbf = np.where(np.isfinite(zbody), zbody, zb_b)
zenv_img = gaussian_filter(_med(zbf, size=21, mode='nearest'), 4)       # robust smooth chest height (small shards/spikes ignored)
def zenv(x, y): return samp(zenv_img, x, y)
def zfront(x, y):
    ok = samp(np.isfinite(zbody).astype(float), x, y) > 0.999
    z = samp(np.where(np.isfinite(zbody), zbody, 0.0), x, y)
    return np.where(ok, z, samp(zb_s, x, y))
sel = Fb[(P[Fb][:, :, 1].min(1) > 1.25) & (np.abs(P[Fb][:, :, 0]).max(1) < 0.25) & (np.abs(P[Fb][:, :, 2]).max(1) < 0.16)]
HB = (-0.25, 0.25, -0.16, 0.16); HS = 1000
Hz, _, hs = depthmap(P[:, [0, 2, 1]]*[-1, 1, -1], sel, HB, int((HB[1]-HB[0])*HS), int((HB[3]-HB[2])*HS))
def hfield(x, z):
    c = np.clip(np.round((x-HB[0])*hs-.5).astype(int), 0, Hz.shape[1]-1); r = np.clip(np.round((HB[3]-z)*hs-.5).astype(int), 0, Hz.shape[0]-1)
    return Hz[r, c]
def smoothstep(a, b, x): t = np.clip((x-a)/(b-a), 0, 1); return t*t*(3-2*t)

# ------------------------------------------------------------------ obstacle samples (body surface, y>1.06) with outward normals
Fbr = Fb[(P[Fb][:, :, 1].mean(1) > 1.06) & (np.abs(P[Fb][:, :, 0].mean(1)) < 0.24)]
Tb = P[Fbr]; fnb = np.cross(Tb[:, 1]-Tb[:, 0], Tb[:, 2]-Tb[:, 0]); ab = np.linalg.norm(fnb, axis=1)
okb = ab > 1e-12; Tb = Tb[okb]; fnb = fnb[okb]/ab[okb, None]
ctr = Tb.mean(1); rr = np.c_[ctr[:, 0], np.zeros(len(ctr)), ctr[:, 2]-zc0]
rr[:, 1] = np.where(ctr[:, 1] > 1.43, 0.3*np.linalg.norm(rr, axis=1), 0)
fnb[(fnb*rr).sum(1) < 0] *= -1
SP, SN = [], []
for a in np.linspace(0, 1, 9):
    for b in np.linspace(0, 1-a, max(int(round((1-a)*8)), 0)+1):
        SP.append(Tb[:, 0]*(1-a-b)+Tb[:, 1]*a+Tb[:, 2]*b); SN.append(fnb)
SP = np.vstack(SP); SN = np.vstack(SN)
tree = cKDTree(SP)
def pushdir(Q):
    rad = np.c_[Q[:, 0], np.zeros(len(Q)), Q[:, 2]-zc0]; rad /= np.linalg.norm(rad, axis=1, keepdims=True)+1e-12
    ru = rad + [0, 0.7, 0]; ru /= np.linalg.norm(ru, axis=1, keepdims=True)
    w = smoothstep(-0.01, 0.02, Q[:, 2])[:, None]
    dv = w*[0, 0, 1.0] + (1-w)*ru; return dv/np.linalg.norm(dv, axis=1, keepdims=True)
def push(Pts, mask, clear=0.003, it=1):
    # move a point out of the body along the normal of the sample it violates most (chest) / the neck push direction (neck); max 4 mm per call
    for _ in range(it):
        Q = Pts[mask]; d, k = tree.query(Q, k=6)
        viol = np.zeros((len(Q), k.shape[1]))
        for col in range(k.shape[1]):
            qp = SP[k[:, col]]; n = SN[k[:, col]]; dist = ((Q-qp)*n).sum(1)
            viol[:, col] = np.where((d[:, col] < 0.006) & (dist < clear), clear-dist, 0.0)
        kb = np.argmax(viol, axis=1); vm = viol[np.arange(len(Q)), kb]; nb = SN[k[np.arange(len(Q)), kb]]
        vm = np.where((Q[:, 2] > 0.04) & (Q[:, 1] < 1.40), 0.0, vm)            # chest: shape comes from the smooth envelope, base spikes are sunk afterwards
        dvc = pushdir(Q); w = smoothstep(0.0, 0.03, Q[:, 2])[:, None]
        dv = w*nb + (1-w)*dvc; dv /= np.linalg.norm(dv, axis=1, keepdims=True)
        dn = np.maximum((dv*nb).sum(1), 0.5)
        Pts[mask] = Q + np.minimum(vm/dn, 0.004)[:, None]*dv
    return Pts

# ------------------------------------------------------------------ helpers
def arcl(C): return np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
def resample3(C, k):
    a = arcl(C); t = np.linspace(0, a[-1], k); return np.c_[[np.interp(t, a, C[:, d]) for d in range(3)]].T
def light_smooth(C, sig):                       # smooth interior, keep end points
    out = C.copy()
    for d in range(3): out[:, d] = gaussian_filter1d(np.r_[[C[0, d]]*8, C[:, d], [C[-1, d]]*8], sig, mode='nearest')[8:-8]
    out[0] = C[0]; out[-1] = C[-1]; return out
def polar_pt(side, r, y, phi_deg):
    ph = np.radians(side*np.asarray(phi_deg, float)); return np.c_[r*np.sin(ph), y, zc0-r*np.cos(ph)]
def body_opening(side):
    V = np.unique(Fb.ravel()); V = V[(np.sign(P[V, 0]) == side) & (P[V, 2] > 0.0)]
    yy = np.arange(1.12, 1.445, 0.01); xx = []
    for y in yy:
        m = np.abs(P[V, 1]-y) < 0.006; xx.append(np.abs(P[V[m], 0]).min())
    return np.polyfit(yy, xx, 3)
from scipy.ndimage import median_filter
OVER = 0.002                                      # inner edge overhangs the body edge by 2 mm (no strip of body edge visible)
def opening_edge(side):
    V = np.unique(Fb.ravel()); V = V[(np.sign(P[V, 0]) == side) & (P[V, 2] > 0.0)]
    yy = np.arange(1.100, 1.436, 0.004); raw = np.full(len(yy), np.nan)
    for k, y in enumerate(yy):
        m = np.abs(P[V, 1]-y) < 0.004
        if m.any(): raw[k] = np.abs(P[V[m], 0]).min()
    ok = np.isfinite(raw); raw = np.interp(yy, yy[ok], raw[ok])
    from scipy.ndimage import minimum_filter1d
    lo = gaussian_filter1d(minimum_filter1d(raw, 7, mode='nearest'), 3, mode='nearest')          # lower envelope of the (ragged) body edge
    sel_ = (yy > 1.11) & (yy < 1.42)
    pf = np.polyfit(yy[sel_], lo[sel_], 4); pv = np.polyval(pf, yy)
    env = gaussian_filter1d(np.minimum(pv, lo), 2, mode='nearest')
    return lambda y: np.interp(y, yy, env)
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

# ------------------------------------------------------------------ edge curves per side (x>0 convention for 'side' = +1; side -1 mirrored inside)
OUT_Y = np.array([1.15, 1.19, 1.23, 1.27, 1.31, 1.345, 1.375, 1.40])
OUT_X = np.array([0.040, 0.066, 0.088, 0.106, 0.1195, 0.1245, 0.1195, 0.1125])
po_out = PchipInterpolator(OUT_Y, OUT_X)
FOLD_K = [(0, 0.073, 1.488), (40, 0.074, 1.485), (70, 0.075, 1.476), (100, 0.075, 1.462), (122, 0.0725, 1.447)]
PHG = 122.0
FALL_K = [(0, 0.0865), (35, 0.0860), (65, 0.097), (90, 0.108), (104, 0.1065)]
PHQ = 104.0
fr_ = PchipInterpolator([k[0] for k in FOLD_K], [k[1] for k in FOLD_K]); fy_ = PchipInterpolator([k[0] for k in FOLD_K], [k[2] for k in FOLD_K])
lr_ = PchipInterpolator([k[0] for k in FALL_K], [k[1] for k in FALL_K])
ph_ = np.linspace(0, PHQ, 209); a_ = np.radians(ph_); r_ = lr_(ph_)
h_ = hfield(r_*np.sin(a_), zc0-r_*np.cos(a_))+0.002
bad = ~np.isfinite(h_) | (h_ < 1.30); h_ = np.interp(ph_, ph_[~bad], h_[~bad])
h_ = gaussian_filter1d(np.r_[[h_[0]]*12, h_, [h_[-1]]*12], 4)[12:-12]
ly_ = lambda x: np.interp(x, ph_, h_)

def side_curves(side):
    pi_ = opening_edge(side)
    # ---- inner (fold) curve: front edge up to y 1.42, then to G, then fold curve round the neck to the centre back
    yA = np.linspace(B0y, 1.42, 90); xA = pi_(yA) - OVER*smoothstep(B0y, 1.14, yA)
    zA = zenv(side*(xA+0.005), yA) + LIFT_IN
    Ic = np.c_[side*xA, yA, zA]
    phf = np.linspace(PHG, 0, 70)
    If = polar_pt(side, fr_(phf), fy_(phf), phf)
    # ---- outer (fall) curve: chest sweep, then fall curve
    yO = np.linspace(B0y, 1.40, 100); xin = pi_(yO) - OVER*smoothstep(B0y, 1.14, yO)
    tap = smoothstep(B0y, 1.16, yO)
    xo = xin + (po_out(np.maximum(yO, 1.15)) - xin)*tap
    xo = np.where(yO >= 1.15, np.where(tap >= 1, po_out(np.maximum(yO, 1.15)), xo), xo)
    zO = zenv(side*xo, yO) + LIFT_OUT
    Oc = np.c_[side*xo, yO, zO]
    phq = np.linspace(PHQ, 0, 70)
    Of = polar_pt(side, lr_(phq), ly_(phq), phq)
    out = []
    for C1, C2 in ((Ic, If), (Oc, Of)):
        c1 = light_smooth(C1, 1.5); c2 = light_smooth(C2, 1.5)
        a1 = resample3(c1, NS1+1); a2 = resample3(c2, NS2+1)      # seg1: tip -> anchor, seg2: anchor -> centre back
        out.append(np.vstack([a1, a2[1:]]))
    I, O = out
    I[0] = O[0] = 0.5*(I[0]+O[0])                                 # tip: both edges meet in one point
    return I, O

bulge_w = lambda v: np.sin(np.pi*v)
sides = {}
for sd in (-1, 1): sides[sd] = side_curves(sd)
# assemble the full grid: columns left tip -> left centre(=NS) -> right ... -> right tip
tv = np.linspace(0, 1, Mv+1)
def cross_lines(I, O):
    S = (1-tv[None, :, None])*I[:, None, :]+tv[None, :, None]*O[:, None, :]
    dv = pushdir(S.reshape(-1, 3)).reshape(S.shape)
    return S + (BULGE*bulge_w(tv))[None, :, None]*dv
SL = cross_lines(*sides[-1])           # (NS+1, Mv+1, 3), s = tip..centre
SR = cross_lines(*sides[1])
SR[NS] = SL[NS] = 0.5*(SL[NS]+SR[NS])  # shared centre column (x=0 by symmetry)
Cg = np.concatenate([SL, SR[::-1][1:]], axis=0)    # (Mu+1, Mv+1, 3)
assert Cg.shape[0] == Mu+1
Cp = Cg.reshape(-1, 3).copy()
Ig = np.zeros((Mu+1, Mv+1), bool)
fixed = np.zeros((Mu+1, Mv+1), bool); fixed[:, 0] = True; fixed[0, :] = True; fixed[Mu, :] = True
fallm = np.zeros((Mu+1, Mv+1), bool); fallm[1:Mu, Mv] = True
fixed = fixed.ravel(); fallm = fallm.ravel()
def clearance(Cp_):
    d, k = tree.query(Cp_); return ((Cp_-SP[k])*SN[k]).sum(1)
def crease_report(Cp_, tag):
    G_ = Cp_.reshape(Mu+1, Mv+1, 3)
    n_ = np.cross(G_[1:, 1:]-G_[:-1, :-1], G_[:-1, 1:]-G_[1:, :-1]); n_ /= np.linalg.norm(n_, axis=2, keepdims=True)+1e-12
    au = np.degrees(np.arccos(np.clip((n_[1:]*n_[:-1]).sum(2), -1, 1))); av = np.degrees(np.arccos(np.clip((n_[:, 1:]*n_[:, :-1]).sum(2), -1, 1)))
    cl = clearance(Cp_)
    print('%s: cells>25deg along %d across %d (of %d) | max angle along %.1f across %.1f | clearance min %.1f mm, <1mm: %d, <0: %d' % (
        tag, (au > 25).sum(), (av > 25).sum(), au.size, au.max(), av.max(), cl.min()*1000, (cl < 0.001).sum(), (cl < 0).sum()))
Cg0 = Cp.reshape(Mu+1, Mv+1, 3)
chest_cols = np.r_[np.arange(1, NS1+1), np.arange(Mu-NS1, Mu)]
crease_report(Cp, '0 raw')
bm = np.zeros((Mu+1, Mv+1), bool); bm[0, :] = bm[-1, :] = bm[:, 0] = bm[:, -1] = True
for it in range(80):
    Cp = push(Cp, ~fixed & ~fallm)
    dB, kB = tree.query(Cp[fallm]); nB = SN[kB]
    dist = ((Cp[fallm]-SP[kB])*nB).sum(1); dvf = pushdir(Cp[fallm]); dn = np.maximum((dvf*nB).sum(1), 0.3)
    Cp[fallm] -= np.clip((dist-0.0025)/dn, -0.004, 0.004)[:, None]*dvf*0.5
    Cg = Cp.reshape(Mu+1, Mv+1, 3); L = Cg.copy()
    L[1:-1, 1:-1] = 0.25*(Cg[:-2, 1:-1]+Cg[2:, 1:-1]+Cg[1:-1, :-2]+Cg[1:-1, 2:])
    L[1:-1, Mv] = 0.5*(Cg[:-2, Mv]+Cg[2:, Mv])
    sm = np.ones((Mu+1, Mv+1), bool); sm[0, :] = sm[-1, :] = False; sm[:, 0] = False
    Cg = np.where(sm[:, :, None], 0.5*Cg+0.5*L, Cg); Cp = Cg.reshape(-1, 3)
    if it in (0, 19, 79): crease_report(Cp, '1 iter %d' % it)
Cg = Cp.reshape(Mu+1, Mv+1, 3)
for j in range(Mv-3, Mv):
    t_ = (j-(Mv-4))/4.0; Cg[1:Mu, j] = (1-t_)*Cg[1:Mu, Mv-4]+t_*Cg[1:Mu, Mv]
Cp = Cg.reshape(-1, 3)
lastrows = np.zeros((Mu+1, Mv+1), bool); lastrows[:, Mv-4:] = True
Cp = push(Cp, ~fixed & ~fallm & ~lastrows.ravel(), it=3)
Cg = Cp.reshape(Mu+1, Mv+1, 3)
for sig in (3.0, 2.0):                         # along-the-edge smoothing of all free rows (removes sawtooth left by the push)
    Cs = gaussian_filter1d(Cg, sig, axis=0, mode='nearest'); w = np.zeros((Mu+1, 1, 1)); w[4:Mu-3] = 1
    Cg[:, 1:Mv] = (w*Cs + (1-w)*Cg)[:, 1:Mv]
Cp = Cg.reshape(-1, 3)
crease_report(Cp, '2 final')
CT = grid_tris(Mu, Mv)
# drop exactly degenerate triangles (tip columns)
Tq = Cp[CT]; ar = np.linalg.norm(np.cross(Tq[:, 1]-Tq[:, 0], Tq[:, 2]-Tq[:, 0]), axis=1)/2
keep = ar > 1e-10; print('degenerate tris dropped', (~keep).sum())
cn = vnorm(Cp, CT[keep])
cen = Cp[CT[keep]].mean(1); radc = np.c_[cen[:, 0], 0.3*np.hypot(cen[:, 0], cen[:, 2]-zc0)*(cen[:, 1] > 1.43), cen[:, 2]-zc0]
fnn = np.cross(Cp[CT[keep][:, 1]]-Cp[CT[keep][:, 0]], Cp[CT[keep][:, 2]]-Cp[CT[keep][:, 0]])
flip = ((fnn*radc).sum(1) < 0).mean() > 0.5
print('orientation flipped:', flip)
if flip: CT = CT[:, [0, 2, 1]]; cn = -cn
Cg = Cp.reshape(Mu+1, Mv+1, 3)

# ------------------------------------------------------------------ UV: unfold each half from the anchor column iG towards the centre back
UV0 = np.zeros((Mu+1, Mv+1, 2)); UV1 = np.zeros((Mu+1, Mv+1, 2))
tc = np.zeros((Mu+1, Mv+1)); tc[:, 1:] = np.cumsum(np.linalg.norm(np.diff(Cg, axis=1), axis=2), axis=1)
for sd, cols in ((-1, list(range(0, NS+1))), (1, list(range(Mu, NS-1, -1)))):
    c0, c1 = fit[sd]; iG = cols[NS1]
    X2 = np.zeros((len(cols), Mv+1)); Y2 = np.zeros((len(cols), Mv+1))
    wsum = np.zeros(Mv+1)
    for q, ci in enumerate(cols):
        if q <= NS1: X2[q] = Cg[ci, :, 0]; Y2[q] = Cg[ci, :, 1]
        else:
            wsum = wsum + np.linalg.norm(Cg[ci]-Cg[cols[q-1]], axis=1)
            X2[q] = Cg[iG, :, 0] + sd*(tc[ci]-tc[iG]); Y2[q] = Cg[iG, :, 1] + wsum
    for q, ci in enumerate(cols):
        A = np.c_[X2[q], Y2[q], np.ones(Mv+1)]; UV0[ci] = A@c0; UV1[ci] = A@c1
UV0[NS] = UV1[NS] = 0  # placeholder, set below
for sd in (-1, 1):
    pass
# centre column = average of what each side gives
def side_uv(sd):
    c0, c1 = fit[sd]; cols = list(range(0, NS+1)) if sd == -1 else list(range(Mu, NS-1, -1)); iG = cols[NS1]; wsum = np.zeros(Mv+1)
    for q, ci in enumerate(cols):
        if q > NS1: wsum = wsum + np.linalg.norm(Cg[ci]-Cg[cols[q-1]], axis=1)
    ci = NS; A = np.c_[Cg[iG, :, 0] + sd*(tc[ci]-tc[iG]), Cg[iG, :, 1] + wsum, np.ones(Mv+1)]
    return A@c0, A@c1
a0, a1 = side_uv(-1); b0, b1 = side_uv(1); UV0[NS] = 0.5*(a0+b0); UV1[NS] = 0.5*(a1+b1)
print('centre-column UV mismatch left/right (units): U0 %.3f U1 %.3f' % (np.abs(a0-b0).max(), np.abs(a1-b1).max()))

# ------------------------------------------------------------------ edge walls (sunk 1.2 mm into the body, max 4-5 mm); none on the fold edge at the neck
def wall(E, drop_to):
    k = len(E); Wt = np.vstack([E, drop_to]); WT = []
    for q in range(k-1): WT += [[q, q+1, k+q+1], [q, k+q+1, k+q]]
    return Wt, np.array(WT)
# --- base vertices that stick up through the sheet (shards left in the base) are sunk 1.5 mm under it (topology unchanged, no holes)
Pbase = P.copy()
CTk = CT[keep]
zsh, _, ss = depthmap(Cp * [-1, 1, -1], CTk, BOX, W, H)
vb = np.unique(Fb.ravel()); vb = vb[(Pbase[vb, 1] > 1.09) & (Pbase[vb, 1] < 1.425) & (Pbase[vb, 2] > 0.04)]
cc_ = np.clip(((Pbase[vb, 0]-BOX[0])*ss).astype(int), 1, W-2); rr_ = np.clip(((BOX[3]-Pbase[vb, 1])*ss).astype(int), 1, H-2)
from scipy.ndimage import maximum_filter
zsh_d = maximum_filter(np.where(np.isfinite(zsh), zsh, -np.inf), size=13)    # sheet height extended 6 mm past its edges
zs = zsh_d[rr_, cc_]; inside = np.isfinite(zs)
pierce = inside & (Pbase[vb, 2] > zs-0.0015)
print('base vertices sunk under the sheet: %d (max %.1f mm)' % (pierce.sum(), ((Pbase[vb, 2]-(zs-0.0015))[pierce]).max()*1000 if pierce.any() else 0))
Pbase[vb[pierce], 2] = zs[pierce]-0.0015
P = Pbase
# --- body triangles that still cross above the sheet (long shard triangles joining sunk and unsunk vertices): delete them (hidden under the sheet)
tz = Pbase[Fb]; zmask = (tz[:, :, 1].mean(1) > 1.09) & (tz[:, :, 1].mean(1) < 1.425) & (tz[:, :, 2].mean(1) > 0.04) & (np.abs(tz[:, :, 0].mean(1)) < 0.16)
cand = np.where(zmask)[0]; bad_t = np.zeros(len(Fb), bool)
for a_ in np.linspace(0, 1, 6):
    for b_ in np.linspace(0, 1-a_, 6):
        q = tz[cand, 0]*(1-a_-b_)+tz[cand, 1]*a_+tz[cand, 2]*b_
        cc2 = np.clip(((q[:, 0]-BOX[0])*ss).astype(int), 0, W-1); rr2 = np.clip(((BOX[3]-q[:, 1])*ss).astype(int), 0, H-1)
        zz2 = zsh[rr2, cc2]; bad_t[cand[np.isfinite(zz2) & (q[:, 2] > zz2-0.0004)]] = True
print('body triangles still above the sheet, removed:', bad_t.sum())
Fb_out = Fb[~bad_t]
newP = [Cp]; newN = [cn]; newUa = [UV0.reshape(-1, 2)]; newUb = [UV1.reshape(-1, 2)]; newT = [CT[keep] if not flip else CT[keep]]
base = len(P)
newT = [CT[keep]+base]
off = len(Cp)
def add_wall(idx_list, lim, taper_end=0, const=None):
    global off
    E = Cp[idx_list]; d, k = tree.query(E); n = SN[k]
    dist = ((E-SP[k])*n).sum(1); dd = np.clip(dist+0.0018, 0, lim)
    dv = pushdir(E); drop = E - (dd/np.maximum((dv*n).sum(1), 0.3))[:, None]*dv
    if taper_end:
        w = np.ones(len(E)); w[-taper_end:] = np.linspace(1, 0, taper_end); drop = E + (drop-E)*w[:, None]
    Wt, WT = wall(E, drop)
    wn = np.cross(Wt[WT[:, 1]]-Wt[WT[:, 0]], Wt[WT[:, 2]]-Wt[WT[:, 0]]); wc = Wt[WT].mean(1)
    cc = Cp.mean(0)*0 + np.array([0, 1.38, 0.05])
    ref = (wc - cc); ref[:, 1] = 0
    fl = (wn*ref).sum(1) < 0; WT = WT.copy(); WT[fl] = WT[fl][:, [0, 2, 1]]
    uva = np.vstack([UV0.reshape(-1, 2)[idx_list]]*2); uvb = np.vstack([UV1.reshape(-1, 2)[idx_list]]*2)
    newP.append(Wt); newN.append(vnorm(Wt, WT)); newUa.append(uva); newUb.append(uvb); newT.append(WT+base+off); off += len(Wt)
idx = lambda i, j: i*(Mv+1)+j
# outer edge, whole loop (left tip .. back .. right tip) in two runs so the walls are not joined across the tips
add_wall([idx(i, Mv) for i in range(1, Mu)], 0.005, const=0.0035)
# inner edge walls on the chest part of each side (tip to anchor), fading out toward the neck
# (inner walls removed: they produced stray blocks) add_wall([idx(i, 0) for i in range(1, NS1+1)], 0.003, taper_end=14, const=0.0025)
# (inner walls removed: they produced stray blocks) add_wall([idx(i, 0) for i in range(Mu-1, Mu-NS1-1, -1)], 0.003, taper_end=14, const=0.0025)

newP = np.vstack(newP); Fnew = np.vstack(newT)
PP = np.vstack([P, newP]); NN = np.vstack([N, np.vstack(newN)]); UU0 = np.vstack([U0, np.vstack(newUa)]); UU1 = np.vstack([U1, np.vstack(newUb)])
bl = bytearray(blob)
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    o = len(bl); bl.extend(data.tobytes())
    g.bufferViews.append(BufferView(buffer=0, byteOffset=o, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews)-1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
    return len(g.accessors)-1
ids = [addacc(PP.astype('<f4'), 'VEC3', 5126, 34962, PP.astype('<f4').min(0).tolist(), PP.astype('<f4').max(0).tolist()),
       addacc(NN.astype('<f4'), 'VEC3', 5126, 34962), addacc(UU0.astype('<f4'), 'VEC2', 5126, 34962), addacc(UU1.astype('<f4'), 'VEC2', 5126, 34962)]
for p in pr:
    p.attributes.POSITION, p.attributes.NORMAL, p.attributes.TEXCOORD_0, p.attributes.TEXCOORD_1 = ids
mat = copy.deepcopy(g.materials[[i for i, m in enumerate(g.materials) if m.name == 'Jacket_Lapel_Peak'][0]]); mat.name = 'Jacket_Lapel_Shawl'
g.materials.append(mat)
newprim = copy.deepcopy(pr[0]); newprim.material = len(g.materials)-1
newprim.indices = addacc(Fnew.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
pr.append(newprim)
pr[0].indices = addacc(Fb_out.astype('<u4').ravel(), 'SCALAR', 5125, 34963)
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
print('shawl verts', len(newP), 'tris', len(Fnew), 'saved', dst)
np.save('/home/claude/work/sh/shawl_grid.npy', Cg)
