import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); pr=g.meshes[1].primitives
ipk=[i for i,p in enumerate(pr) if g.materials[p.material].name=='Jacket_Lapel_Peak'][0]
Fb=Fs[0]; Fp=Fs[ipk]
sel=Fb[(P[Fb][:,:,1].min(1)>1.25)&(np.abs(P[Fb][:,:,0]).max(1)<0.25)&(np.abs(P[Fb][:,:,2]).max(1)<0.16)]
HB=(-0.25,0.25,-0.16,0.16); HS=1000
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,HB,500,320)
def hf(x,z):
    c=int(np.clip(round((x-HB[0])*hs-.5),0,499)); r=int(np.clip(round((HB[3]-z)*hs-.5),0,319)); return Hz[r,c]
# collar verts = last ones: find by index of the biggest grid: use boundary edges of Fp (open edges) lower than 1.46 behind z<0.0
from collections import Counter
E=Counter()
for t in Fp:
    for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])): E[tuple(sorted((a,b)))]+=1
bd=[e for e,c in E.items() if c==1]
print('open boundary edges in peak primitive',len(bd))
zc0=-0.005
rows=[]
for a,b in bd:
    m=(P[a]+P[b])/2
    if m[2]<0.0 and m[1]>1.40:
        h=hf(m[0],m[2]); phi=np.degrees(np.arctan2(m[0],-(m[2]-zc0)))
        rows.append((phi,m[1]-h if np.isfinite(h) else np.nan,m))
rows.sort(key=lambda r:r[0])
print('back/side open edges: phi, height above body (mm) [nan=no body under]')
for lo in range(-120,121,10):
    s=[r[1] for r in rows if lo<=r[0]<lo+10 and np.isfinite(r[1])]
    if s: print('%4d..%4d n%3d  min %5.1f  max %5.1f  mean %5.1f'%(lo,lo+10,len(s),min(s)*1000,max(s)*1000,np.mean(s)*1000))
