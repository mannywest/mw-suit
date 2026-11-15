import sys, collections, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
g,blob,P,N,U0,U1,Fs=load('/home/claude/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb')
pr=g.meshes[1].primitives
print([ (g.materials[p.material].name,len(f)) for p,f in zip(pr,Fs)], 'nverts',len(P))
ipk=[i for i,p in enumerate(pr) if g.materials[p.material].name=='Jacket_Lapel_Peak'][0]
Fb,Fp=Fs[0],Fs[ipk]
par=np.arange(len(P))
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for t in Fp:
    for a,b in ((t[0],t[1]),(t[1],t[2])):
        ra,rb=f(a),f(b)
        if ra!=rb: par[ra]=rb
lab=np.array([f(t[0]) for t in Fp]); top2=[k for k,_ in collections.Counter(lab).most_common(2)]
lap=np.isin(lab,top2); Fc=Fp[~lap]
print('collar tris',len(Fc),'islands',len(set(lab[~lap])))
zc0=-0.005
def ang(V): return np.degrees(np.arctan2(P[V,0],-(P[V,2]-zc0)))
Vc=np.unique(Fc.ravel()); Vb=np.unique(Fb.ravel()); Vb=Vb[(P[Vb,1]>1.30)&(np.abs(P[Vb,0])<0.2)]
print('phi  | collar: n  y_min y_max  r_min r_max | body(y>1.30): top y at r<0.10 / r range of top')
for lo in range(-120,121,10):
    hi=lo+10
    m=(ang(Vc)>=lo)&(ang(Vc)<hi); mb=(ang(Vb)>=lo)&(ang(Vb)<hi)
    s=''
    if m.any():
        V=Vc[m]; r=np.hypot(P[V,0],P[V,2]-zc0)
        s+='n%4d y %.3f..%.3f r %.3f..%.3f'%(m.sum(),P[V,1].min(),P[V,1].max(),r.min(),r.max())
    if mb.any():
        V=Vb[mb]; r=np.hypot(P[V,0],P[V,2]-zc0); j=np.argmax(P[V,1])
        s+=' | body top y %.3f at r %.3f ; r range %.3f..%.3f'%(P[V[j],1],r[j],r.min(),r.max())
    print('%4d..%4d %s'%(lo,hi,s))
print('--- cross-section profiles (r,y) mm: collar bins, body top ring')
for c in (0,30,60,90,110):
    for sgn in ((1,) if c==0 else (1,)):
        m=(np.abs(ang(Vc)-c)<4); V=Vc[m]; r=np.hypot(P[V,0],P[V,2]-zc0)
        o=np.argsort(P[V,1]); 
        yy=np.linspace(P[V,1].min(),P[V,1].max(),7)
        out=[]
        for k in range(6):
            q=(P[V,1]>=yy[k])&(P[V,1]<=yy[k+1])
            if q.any(): out.append('y%.1f:r%.0f-%.0f'%(np.mean(P[V[q],1])*1000,r[q].min()*1000,r[q].max()*1000))
        print('collar phi~%d'%c,' '.join(out))
        mb=(np.abs(ang(Vb)-c)<4)&(P[Vb,1]>1.40); VB=Vb[mb]; rb=np.hypot(P[VB,0],P[VB,2]-zc0)
        yy=np.linspace(1.40,P[VB,1].max(),7); out=[]
        for k in range(6):
            q=(P[VB,1]>=yy[k])&(P[VB,1]<=yy[k+1])
            if q.any(): out.append('y%.1f:r%.0f-%.0f'%(np.mean(P[VB[q],1])*1000,rb[q].min()*1000,rb[q].max()*1000))
        print('   body  phi~%d'%c,' '.join(out))
# front ends: where collar y/z reach toward front (|phi|>110)
m=np.abs(ang(Vc))>=110
print('collar verts |phi|>=110: z range %.3f..%.3f'%(P[Vc[m],2].min(),P[Vc[m],2].max()))
