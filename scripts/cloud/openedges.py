import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=np.vstack(Fs[:3])
# weld by position
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
T=inv[F]; E=np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1); u,c=np.unique(E,axis=0,return_counts=True)
op=u[c==1]; rep={}
for i,p in enumerate(P): rep.setdefault(inv[i],p)
pts=np.array([[rep[a],rep[b]] for a,b in op])*1000
m=(np.abs(pts[:,:,0]).min(1)>40)&(np.abs(pts[:,:,0]).max(1)<70)&(pts[:,:,2].max(1)<-50)&(pts[:,:,1].min(1)>1430)
print(m.sum(),'open edges in zone'); 
for e in pts[m][:40]: print(np.round(e[0]),np.round(e[1]))
