# Base build G: remove sliver triangles at the front closure (the black line seen through the neck opening from above).
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
src,out=sys.argv[1],sys.argv[2]
g,blob,P,N,U0,U1,Fs=load(src); pr=g.meshes[1].primitives; F=Fs[0]; Q=P[F]; c=Q.mean(1)
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2
e=np.stack([np.linalg.norm(Q[:,1]-Q[:,0],axis=1),np.linalg.norm(Q[:,2]-Q[:,1],axis=1),np.linalg.norm(Q[:,0]-Q[:,2],axis=1)],1); asp=e.max(1)**2/np.maximum(2*ar,1e-12)
sl=(np.abs(c[:,0])<0.06)&(c[:,2]>0.15)&(c[:,1]>0.85)&(c[:,1]<1.25)&(asp>60)&(ar<8e-6)
print('closure slivers removed:',sl.sum()); Fn=F[~sl]
ia=g.accessors[pr[0].indices]; ibv=g.bufferViews[ia.bufferView]; ioff=(ibv.byteOffset or 0)+(ia.byteOffset or 0)
dt={5123:'<u2',5125:'<u4'}[ia.componentType]; buf=bytearray(g.binary_blob()); buf[ioff:ioff+len(Fn)*3*np.dtype(dt).itemsize]=Fn.astype(dt).ravel().tobytes(); ia.count=len(Fn)*3
g.set_binary_blob(bytes(buf)); g.save(out)
