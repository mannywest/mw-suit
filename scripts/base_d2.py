# Base build D: remove small shard triangles (facing down / inward, tiny) at the front sides of the neck.
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
src,out=sys.argv[1],sys.argv[2]; AMAX=float(sys.argv[3]) if len(sys.argv)>3 else 20e-6; NY=float(sys.argv[4]) if len(sys.argv)>4 else -0.2
g,blob,P,N,U0,U1,Fs=load(src); pr=g.meshes[1].primitives; F=Fs[0]; Q=P[F]; c=Q.mean(1); ZC=-0.005
n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; ny=n[:,1]/np.maximum(2*ar,1e-12)
ph=np.degrees(np.arctan2(c[:,0],-(c[:,2]-ZC))); r=np.hypot(c[:,0],c[:,2]-ZC)
sh=(c[:,1]>1.395)&(r<0.115)&(r>0.07)&(np.abs(ph)<92)&(ny<NY)&(ar<AMAX)
print('shard triangles removed:',sh.sum()); Fn=F[~sh]
ia=g.accessors[pr[0].indices]; ibv=g.bufferViews[ia.bufferView]; ioff=(ibv.byteOffset or 0)+(ia.byteOffset or 0)
dt={5123:'<u2',5125:'<u4'}[ia.componentType]; buf=bytearray(g.binary_blob()); buf[ioff:ioff+len(Fn)*3*np.dtype(dt).itemsize]=Fn.astype(dt).ravel().tobytes(); ia.count=len(Fn)*3
g.set_binary_blob(bytes(buf)); g.save(out)
