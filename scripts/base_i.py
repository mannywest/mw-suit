# Base build I: make shading normals consistent at the neck rim: any rim vertex whose normal points downward on an upward-facing surface is flipped.
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
src,out=sys.argv[1],sys.argv[2]
g,blob,P,N,U0,U1,Fs=load(src); pr=g.meshes[1].primitives; F=Fs[0]; ZC=-0.005
used=np.zeros(len(P),bool); used[np.unique(F)]=True
r=np.hypot(P[:,0],P[:,2]-ZC); ph=np.degrees(np.arctan2(P[:,0],-(P[:,2]-ZC)))
Q=P[F]; fn=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); fy=np.zeros(len(P)); cnt=np.zeros(len(P))
for k in range(3): np.add.at(fy,F[:,k],fn[:,1]/np.maximum(np.linalg.norm(fn,axis=1),1e-12)); np.add.at(cnt,F[:,k],1)
fy=fy/np.maximum(cnt,1)
zone=used&(P[:,1]>1.395)&(r<0.12)&(np.abs(ph)<100)
bad=zone&(N[:,1]<0)&(fy>0.3)
print('rim vertices with a downward normal on an upward surface:',bad.sum()); Nn=N.copy(); Nn[bad]*=-1
bad2=zone&((Nn*np.c_[np.zeros(len(P)),np.ones(len(P)),np.zeros(len(P))]).sum(1)<0.2)&(fy>0.6)
a=g.accessors[pr[0].attributes.NORMAL]; bv=g.bufferViews[a.bufferView]; off=(bv.byteOffset or 0)+(a.byteOffset or 0)
buf=bytearray(g.binary_blob()); buf[off:off+a.count*12]=Nn.astype('<f4').tobytes(); g.set_binary_blob(bytes(buf)); g.save(out)
