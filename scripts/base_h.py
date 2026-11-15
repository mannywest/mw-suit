# Base build H: recompute smooth normals around the neck rim (area-weighted over faces sharing a position) so the rim strip shades without stars.
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
src,out=sys.argv[1],sys.argv[2]
g,blob,P,N,U0,U1,Fs=load(src); pr=g.meshes[1].primitives; F=Fs[0]; ZC=-0.005
key=np.round(P*1e5).astype(np.int64); uk,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
Q=P[F]; fn=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0])      # area-weighted
acc=np.zeros((len(uk),3))
for k in range(3): np.add.at(acc,inv[F[:,k]],fn)
L=np.linalg.norm(acc,axis=1); acc=acc/np.maximum(L,1e-12)[:,None]
r=np.hypot(P[:,0],P[:,2]-ZC); ph=np.degrees(np.arctan2(P[:,0],-(P[:,2]-ZC)))
used=np.zeros(len(P),bool); used[np.unique(F)]=True
zone=used&(P[:,1]>1.38)&(r<0.14)&(np.abs(ph)<155)&(L[inv]>1e-12)
Nn=N.copy(); new=acc[inv][zone]; old=N[zone]
flip=(new*old).sum(1)<0; new[flip]*=-1
Nn[zone]=new; print('normals recomputed:',zone.sum(),'| mean angle change %.1f deg'%np.degrees(np.arccos(np.clip((new*old).sum(1),-1,1))).mean())
a=g.accessors[pr[0].attributes.NORMAL]; bv=g.bufferViews[a.bufferView]; off=(bv.byteOffset or 0)+(a.byteOffset or 0)
buf=bytearray(g.binary_blob()); buf[off:off+a.count*12]=Nn.astype('<f4').tobytes(); g.set_binary_blob(bytes(buf)); g.save(out)
