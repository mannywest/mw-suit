import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]; c=Q.mean(1); ZC=-0.005
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; n=n/np.maximum(2*ar,1e-12)[:,None]
ph=np.degrees(np.arctan2(c[:,0],-(c[:,2]-ZC))); r=np.hypot(c[:,0],c[:,2]-ZC)
side=int(sys.argv[2]) # +1 right
m=(c[:,1]>1.38)&(r<0.125)&(side*ph>95)&(side*ph<160)
print('zone tris',m.sum(),'area %.0f mm2'%(ar[m].sum()*1e6))
rad=np.c_[c[:,0],c[:,2]-ZC]; rad=rad/np.linalg.norm(rad,axis=1)[:,None]; nr=(n[:,[0,2]]*rad).sum(1)
# layers: for each tri, how many other zone tris lie above it in top view (height field of zone vs this tri)
idx=np.where(m)[0]
print('facing: up(ny>0.5) %d | sideways %d | down(ny<-0.3) %d | inward(nr<-0.3) %d'%((n[idx,1]>0.5).sum(),((np.abs(n[idx,1])<=0.5)).sum(),(n[idx,1]<-0.3).sum(),(nr[idx]<-0.3).sum()))
# print a coarse table: phi bin, r bin, mean y, count
for t in idx[np.argsort(-c[idx,1])][:14]:
    print(np.round(Q[t]*1000).astype(int).tolist(),'ph %.0f r %.0f ny %.2f nr %.2f area %.0f'%(ph[t],r[t]*1000,n[t,1],nr[t],ar[t]*1e6))
