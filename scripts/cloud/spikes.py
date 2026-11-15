import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]; c=Q.mean(1)
m=(np.abs(c[:,0])<0.03)&(c[:,2]<-0.06)&(c[:,2]>-0.095)&(c[:,1]>1.435)
print('tris near back-centre rim:',m.sum())
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; ny=n[:,1]/np.maximum(2*ar,1e-12)
for t in np.where(m)[0][np.argsort(-c[m,1])][:25]:
    print(np.round(Q[t]*1000,1).tolist(),'ny %.2f area %.1f'%(ny[t],ar[t]*1e6))
