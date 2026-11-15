import sys, collections, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
g,blob,P,N,U0,U1,Fs=load('/home/claude/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb')
pr=g.meshes[1].primitives; ipk=[i for i,p in enumerate(pr) if g.materials[p.material].name=='Jacket_Lapel_Peak'][0]; Fp=Fs[ipk]
par=np.arange(len(P))
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for t in Fp:
    for a,b in ((t[0],t[1]),(t[1],t[2])):
        ra,rb=f(a),f(b)
        if ra!=rb: par[ra]=rb
lab=np.array([f(t[0]) for t in Fp]); top2=[k for k,_ in collections.Counter(lab).most_common(2)]
for k in top2:
    V=np.unique(Fp[lab==k].ravel()); M=np.c_[P[V,0],P[V,1],np.ones(len(V))]
    for nm,U in (('U0',U0),('U1',U1)):
        c=np.linalg.lstsq(M,U[V],rcond=None)[0]; r=M@c-U[V]
        print('lapel side x%+.2f %s: dU/dx %.2f dU/dy %.2f | dV/dx %.2f dV/dy %.2f | off %.2f %.2f | rms %.3f'%(np.sign(P[V,0].mean()),nm,c[0,0],c[1,0],c[0,1],c[1,1],c[2,0],c[2,1],np.sqrt((r**2).mean())))
