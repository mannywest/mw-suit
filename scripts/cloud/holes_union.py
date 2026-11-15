import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]; Fp=Fs[1]
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; S=2000
F=np.vstack([Fb[(P[Fb][:,:,1].min(1)>1.30)],Fp])
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],F,(x0,x1,z0,z1),int((x1-x0)*S),int((z1-z0)*S))
emp=~np.isfinite(Hz); lab,n=ndi.label(emp); H,W=emp.shape
print('union empty components',n)
for k in range(1,n+1):
    m=lab==k; a=m.sum()*(1000/hs)**2; rr,cc=np.where(m)
    border=(rr.min()==0 or cc.min()==0 or rr.max()==H-1 or cc.max()==W-1)
    xs=x0+(cc+.5)/hs; zs=z1-(rr+.5)/hs
    if a>=0.3: print('#%d area %7.1f mm2 border=%s  x %.0f..%.0f  z %.0f..%.0f'%(k,a,border,xs.min()*1000,xs.max()*1000,zs.min()*1000,zs.max()*1000))
