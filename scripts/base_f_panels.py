#!/usr/bin/env python3
"""Base repair step F: rebuild each torso SIDE as one smooth panel (replaces the crumpled cloth + step-E patches in that strip).
    python3 scripts/base_f_panels.py IN.glb OUT.glb
Panel = grid in (angle round the torso, height). Radius is blended smoothly between the clean cloth in front of the strip and behind it.
Old triangles whose centre lies inside the strip (torso layer only; sleeves untouched) are removed. The panel runs ~3 mm under the
neighbouring cloth for ~8 degrees each end so there is no crack. Weave coordinates come from base_e_sides.write()."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from common import load
from scipy.ndimage import gaussian_filter1d, median_filter
import base_e_sides as be

ZC = -0.02; LIM = 0.200; TA, TB = 78.0, 124.0; EXT = 8.0; Y_TOP = 0.97; SINK = 0.003; DEL_IN = 4.0


def slice_segments(T, y):
    s = T[:, :, 1] - y; m = (s.min(1) < 0) & (s.max(1) > 0); Tt = T[m]; s = s[m]; segs = []
    for t, ss in zip(Tt, s):
        pts = [t[i] + ss[i] / (ss[i] - ss[(i + 1) % 3]) * (t[(i + 1) % 3] - t[i]) for i in range(3) if ss[i] * ss[(i + 1) % 3] < 0]
        if len(pts) == 2: segs.append([pts[0][[0, 2]], pts[1][[0, 2]]])
    return np.array(segs)


def ray_r(S, th, sgn):
    if len(S) == 0: return np.nan
    d = np.array([sgn * np.sin(np.radians(th)), np.cos(np.radians(th))]); o = np.array([0, ZC]); p = S[:, 0] - o; e = S[:, 1] - S[:, 0]
    den = d[0] * (-e[:, 1]) - d[1] * (-e[:, 0])
    with np.errstate(all='ignore'):
        t = (p[:, 0] * (-e[:, 1]) - p[:, 1] * (-e[:, 0])) / den; u = (d[0] * p[:, 1] - d[1] * p[:, 0]) / den
    ok = (t > 0) & (u >= 0) & (u <= 1) & (t < LIM)
    return t[ok].max() if ok.any() else np.nan


def fillnan(a):
    i = np.arange(len(a)); k = np.isfinite(a)
    return np.interp(i, i[k], a[k]) if k.sum() >= 2 else a


def build(src):
    g, blob, P, N, U0, U1, Fs = load(src); pr = g.meshes[1].primitives
    ib = [i for i, p in enumerate(pr) if g.materials[p.material].name == 'Jacket_Wool'][0]; F = Fs[ib]; T = P[F]
    ys = np.arange(0.72, Y_TOP + 1e-6, 0.005); ths = np.arange(TA - EXT, TB + EXT + 1e-6, 1.5)
    cen = T.mean(1); drop = np.zeros(len(F), bool); fills = []
    for sgn in (1, -1):
        rA = np.full(len(ys), np.nan); rB = rA.copy()
        for k, y in enumerate(ys):
            S = slice_segments(T, y); rA[k] = np.mean([ray_r(S, TA + d, sgn) for d in (-2, 0, 2)]); rB[k] = np.mean([ray_r(S, TB + d, sgn) for d in (-2, 0, 2)])
        rA = gaussian_filter1d(median_filter(fillnan(rA), 7, mode='nearest'), 3); rB = gaussian_filter1d(median_filter(fillnan(rB), 7, mode='nearest'), 3)
        # lowest cloth per angle (hem line)
        th_c = np.degrees(np.arctan2(sgn * cen[:, 0], cen[:, 2] - ZC)); r_c = np.hypot(cen[:, 0], cen[:, 2] - ZC)
        torso = (r_c < LIM) & (np.sign(cen[:, 0]) == sgn)
        yl = []
        for th in ths:
            m = torso & (np.abs(th_c - th) < 3) & (cen[:, 1] < 0.9); yl.append(cen[m, 1].min() if m.any() else np.nan)
        yl = gaussian_filter1d(median_filter(fillnan(np.array(yl)), 5, mode='nearest'), 2)
        yl = np.clip(yl - 0.002, 0.70, 0.80)
        # grid
        NY = 48; V = []; idx = -np.ones((len(ths), NY), int)
        for i, th in enumerate(ths):
            w = np.clip((th - TA) / (TB - TA), 0, 1); w = w * w * (3 - 2 * w)
            for j, y in enumerate(np.linspace(yl[i], Y_TOP, NY)):        # each column starts exactly on the hem line: smooth bottom edge, no steps
                r = np.interp(y, ys, rA) + (np.interp(y, ys, rB) - np.interp(y, ys, rA)) * w
                if th < TA or th > TB: r -= SINK
                if y > Y_TOP - 0.02: r -= SINK * min(1, (y - (Y_TOP - 0.02)) / 0.02)
                idx[i, j] = len(V); V.append([sgn * r * np.sin(np.radians(th)), y, ZC + r * np.cos(np.radians(th))])
        V = np.array(V); Tr = []
        for i in range(len(ths) - 1):
            for j in range(NY - 1):
                q = (idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1])
                if min(q) < 0: continue
                Tr += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
        Tr = np.array(Tr); nn = np.cross(V[Tr[:, 1]] - V[Tr[:, 0]], V[Tr[:, 2]] - V[Tr[:, 0]]); rad = V[Tr].mean(1) - np.array([0, 0, ZC]); rad[:, 1] = 0
        fl = (nn * rad).sum(1) < 0; Tr[fl] = Tr[fl][:, [0, 2, 1]]
        used = np.unique(Tr); rm = -np.ones(len(V), int); rm[used] = np.arange(len(used)); V = V[used]; Tr = rm[Tr]
        fills.append(dict(V=V, T=Tr, dv=None, mm2=0, pos=V.mean(0)))
        inside = torso & (th_c > TA + DEL_IN) & (th_c < TB - DEL_IN) & (cen[:, 1] < Y_TOP - 0.01) & (cen[:, 1] > 0.70)
        drop |= inside
        print('side %+d: rA %.0f..%.0f mm, rB %.0f..%.0f mm, hem line y %.3f..%.3f, panel %d verts %d tris; old triangles removed %d' % (
            sgn, rA.min() * 1000, rA.max() * 1000, rB.min() * 1000, rB.max() * 1000, yl.min(), yl.max(), len(V), len(Tr), inside.sum()))
    return fills, drop


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    fills, drop = build(src); n = be.write(src, dst, fills, drop); print('saved', dst, 'added', n, 'tris')
