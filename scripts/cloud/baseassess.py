import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1])
names=['body Jacket_Wool','lapel(s)/collar prim 1','prim 2']
print('primitives:',len(Fs),[len(f) for f in Fs])
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
def opened(F):
    T=inv[F]; E=np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1); u,c=np.unique(E,axis=0,return_counts=True); return u[c==1],E
Fb=Fs[0]; op,_=opened(Fb)
rep={}
for i,p in enumerate(P): rep.setdefault(inv[i],p)
pts=np.array([[rep[a],rep[b]] for a,b in op])*1000
ln=np.linalg.norm(pts[:,0]-pts[:,1],axis=1)
neck=(pts[:,:,1].min(1)>1380)&(np.abs(pts[:,:,0]).max(1)<200)
print('BODY open edges total',len(op),'| in neck/shoulder zone (y>1380mm):',neck.sum(),'| total length there %.0f mm'%ln[neck].sum())
Vb=np.unique(Fb); print('body vertices above y 1.30 m:',(P[Vb,1]>1.30).sum())
print('body y range %.3f..%.3f'%(P[Vb,1].min(),P[Vb,1].max()))
for k in range(1,len(Fs)):
    V=np.unique(Fs[k]); print('prim',k,'tris',len(Fs[k]),'y %.3f..%.3f'%(P[V,1].min(),P[V,1].max()),'x range %.3f..%.3f'%(P[V,0].min(),P[V,0].max()))
