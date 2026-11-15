import sys, numpy as np
from scipy import ndimage as nd
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]; sel=Fb[(P[Fb][:,:,1].min(1)>1.30)]
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; W=int(.38*2000); H=int(.21*2000)
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,(x0,x1,z0,z1),W,H)
lab,n=nd.label(~np.isfinite(Hz))
for k in range(1,n+1):
    m=lab==k; r,c=np.where(m); print(k,'area %.1f mm2'%(m.sum()*(1000/hs)**2),'x %.0f..%.0f z %.0f..%.0f'%((x0+c.min()/hs)*1000,(x0+c.max()/hs)*1000,(z1-r.max()/hs)*1000,(z1-r.min()/hs)*1000),'border' if (r.min()==0 or c.min()==0 or r.max()==H-1 or c.max()==W-1) else 'enclosed')
