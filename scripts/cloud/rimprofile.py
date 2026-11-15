import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]; sel=Fb[(P[Fb][:,:,1].min(1)>1.25)]
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; hs=2000; W=int(.38*hs); H=int(.21*hs)
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,(x0,x1,z0,z1),W,H)
zc=-0.005
print('phi(0=back,180=front)  rim r(mm)  surface y at rim  max y within 15mm outside rim   [first body cell scanning outward from r=40mm]')
for phi in range(-180,181,15):
    t=np.radians(phi); rr=None
    for r in np.arange(0.04,0.17,0.0005):
        x=r*np.sin(t); z=zc-r*np.cos(t)
        c=int((x-x0)*hs); rw=int((z1-z)*hs)
        if 0<=rw<H and 0<=c<W and np.isfinite(Hz[rw,c]):
            ys=[Hz[int((z1-(zc-(r+d)*np.cos(t)))*hs),int(((r+d)*np.sin(t)-x0)*hs)] for d in np.arange(0,0.015,0.001) if 0<=int((z1-(zc-(r+d)*np.cos(t)))*hs)<H and 0<=int(((r+d)*np.sin(t)-x0)*hs)<W]
            ys=[y for y in ys if np.isfinite(y)]
            rr=(r,Hz[rw,c],max(ys) if ys else np.nan); break
    print('%5d  %s'%(phi,'none' if rr is None else '%6.1f   %7.1f   %7.1f'%(rr[0]*1000,rr[1]*1000,rr[2]*1000)))
