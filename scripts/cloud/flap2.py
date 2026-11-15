import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]; c=Q.mean(1); ZC=-0.005
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; n=n/np.maximum(2*ar,1e-12)[:,None]
ph=np.degrees(np.arctan2(c[:,0],-(c[:,2]-ZC))); r=np.hypot(c[:,0],c[:,2]-ZC)
rad=np.c_[c[:,0],c[:,2]-ZC]; rad=rad/np.linalg.norm(rad,axis=1)[:,None]; nr=(n[:,[0,2]]*rad).sum(1)
m=(c[:,1]>1.395)&(r<0.10)&(ph>95)&(ph<150)&(ar>2e-6)
print('tris',m.sum())
for t in np.where(m)[0][np.argsort(-c[m,1])]:
    print(np.round(c[t]*1000).astype(int).tolist(),'ph %3.0f r %3.0f | n (x %.2f y %.2f z %.2f) nr %.2f area %3.0f'%(ph[t],r[t]*1000,n[t,0],n[t,1],n[t,2],nr[t],ar[t]*1e6))
