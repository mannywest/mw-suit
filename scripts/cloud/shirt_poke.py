import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
from pygltflib import GLTF2
from seam5 import rd
from seam2 import tris
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]; Fp=Fs[1]
sh=[m for m in g.meshes if m.name=='Shirt'][0].primitives[0]
PS=rd(g,blob,sh.attributes.POSITION,3); FS=tris(g,sh.indices)
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; S=2000; box=(x0,x1,z0,z1); W=int((x1-x0)*S); H=int((z1-z0)*S)
F=np.vstack([Fb[(P[Fb][:,:,1].min(1)>1.30)],Fp])
Hj,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],F,box,W,H)
FSs=FS[(PS[FS][:,:,1].min(1)>1.30)]
Hs,_,_=depthmap(PS[:,[0,2,1]]*[-1,1,-1],FSs,box,W,H)
ex=np.where(np.isfinite(Hs)&np.isfinite(Hj),Hs-Hj,np.nan)
# shirt visible above jacket (excess > 1 mm), excluding the neck opening interior (r < 0.085 about axis (0,-0.005))
rr,cc=np.mgrid[0:H,0:W]; X=x0+(cc+.5)/hs; Z=z1-(rr+.5)/hs; R=np.hypot(X,Z+0.005)
poke=(ex>0.001)&(R>0.085)
lab,n=ndi.label(poke)
print('cells where the shirt is above jacket (excess>1mm, r>85mm):',poke.sum(),'components',n)
for k in range(1,n+1):
    m=lab==k; a=m.sum()*(1000/hs)**2
    if a<2: continue
    r_,c_=np.where(m)
    print(' #%d area %6.1f mm2 x %.0f..%.0f z %.0f..%.0f  max excess %.1f mm  (shirt y %.0f jacket y %.0f at worst)'%(k,a,(x0+c_.min()/hs)*1000,(x0+c_.max()/hs)*1000,(z1-r_.max()/hs)*1000,(z1-r_.min()/hs)*1000,np.nanmax(np.where(m,ex,np.nan))*1000,np.nanmax(np.where(m,Hs,np.nan))*1000,np.nanmax(np.where(m,Hj,np.nan))*1000))
