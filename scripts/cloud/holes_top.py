import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; S=2000   # 0.5 mm cells
sel=Fb[(P[Fb][:,:,1].min(1)>1.30)]
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,(x0,x1,z0,z1),int((x1-x0)*S),int((z1-z0)*S))
emp=~np.isfinite(Hz)
lab,n=ndi.label(emp)
print('grid',Hz.shape,'empty components',n)
H,W=emp.shape
for k in range(1,n+1):
    m=lab==k; a=m.sum()*(1000/hs)**2
    rr,cc=np.where(m); border=(rr.min()==0 or cc.min()==0 or rr.max()==H-1 or cc.max()==W-1)
    if a<0.3 or border: continue
    xs=x0+(cc+.5)/hs; zs=z1-(rr+.5)/hs
    ys=[Hz[min(H-1,max(0,r+d)),min(W-1,max(0,c+e))] for r,c in zip(rr[::max(1,len(rr)//40)],cc[::max(1,len(cc)//40)]) for d in (-3,3) for e in (-3,3)]
    ys=np.array([y for y in ys if np.isfinite(y)])
    print('enclosed hole #%d area %.1f mm2  x %.1f..%.1f  z %.1f..%.1f  surrounding y %.0f..%.0f mm'%(k,a,xs.min()*1000,xs.max()*1000,zs.min()*1000,zs.max()*1000,(ys.min()*1000 if len(ys) else 0),(ys.max()*1000 if len(ys) else 0)))
