import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]; Q=P[F]; c=Q.mean(1)
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2
m=(c[:,1]>1.36)&(np.abs(c[:,0])<0.07)&(c[:,2]>0.03)
print('body tris in front-of-neck zone (|x|<70, z>30, y>1360):',m.sum(),' tiny(<3mm2):',(m&(ar<3e-6)).sum())
# thin triangles: long skinny
e=np.stack([np.linalg.norm(Q[:,1]-Q[:,0],axis=1),np.linalg.norm(Q[:,2]-Q[:,1],axis=1),np.linalg.norm(Q[:,0]-Q[:,2],axis=1)],1)
asp=e.max(1)**2/np.maximum(2*ar,1e-12)  # large = skinny
sk=m&(asp>40)
print('skinny:',sk.sum())
for t in np.where(sk)[0][:10]: print(np.round(Q[t]*1000).astype(int).tolist(),'area %.1f aspect %.0f'%(ar[t]*1e6,asp[t]))
# body surface y at front zone vs nothing
print('y range in zone %.0f..%.0f'%(c[m,1].min()*1000,c[m,1].max()*1000))
