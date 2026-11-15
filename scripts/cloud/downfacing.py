import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]; c=Q.mean(1)
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; ny=n[:,1]/np.maximum(2*ar,1e-12)
# compare with stored vertex normals: flipped winding?
vn=N[F].mean(1); fl=(n*vn).sum(1)<0
m=(c[:,1]>1.38)&(np.hypot(c[:,0],c[:,2]+0.005)<0.14)
print('tris in neck zone',m.sum(),'| winding opposite to vertex normals:',(m&fl).sum(),'| facing down (ny<-0.3):',(m&(ny<-0.3)).sum())
for t in np.where(m&(fl|(ny<-0.3)))[0][:15]: print(np.round(Q[t]*1000).astype(int).tolist(),'ny %.2f area %.1f flipped %s'%(ny[t],ar[t]*1e6,fl[t]))
