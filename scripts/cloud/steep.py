import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); a=np.linalg.norm(n,axis=1); ny=np.abs(n[:,1])/np.maximum(a,1e-12)
c=Q.mean(1); r=np.hypot(c[:,0],c[:,2]+0.005); phi=np.degrees(np.arctan2(c[:,0],-(c[:,2]+0.005)))
m=(c[:,1]>1.40)&(r<0.11)&(ny<0.35)&(a/2>1e-7)
print('steep (|ny|<0.35) body tris near neck:',m.sum())
for t in np.where(m)[0]: print(np.round(Q[t]*1000).astype(int).tolist(),'phi %.0f r %.0f ny %.2f area %.1fmm2'%(phi[t],r[t]*1000,ny[t],a[t]/2*1e6))
