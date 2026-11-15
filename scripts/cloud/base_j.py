# Base step J: remove shard triangles (folded / sideways / back-facing micro-geometry) in the front closure zone near the button.
# usage: base_j.py src dst [nzmax]    All vertex data unchanged; only body triangle indices are removed.
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
from pygltflib import Accessor, BufferView
src,dst=sys.argv[1],sys.argv[2]; NZMAX=float(sys.argv[3]) if len(sys.argv)>3 else 0.35
g,blob,P,N,U0,U1,Fs=load(src); pr=g.meshes[1].primitives; F=Fs[0]
T=P[F]; c=T.mean(1); fn=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); ar=np.linalg.norm(fn,axis=1)/2; fn/=np.linalg.norm(fn,axis=1,keepdims=True)+1e-12
zone=(np.abs(c[:,0])<0.055)&(c[:,1]>1.10)&(c[:,1]<1.24)&(c[:,2]>0.12)
bad=zone&(fn[:,2]<NZMAX)
print('zone tris',zone.sum(),'removed',bad.sum(),'area removed mm2 %.0f'%(ar[bad].sum()*1e6))
np.save('/home/claude/work/sh/shard_tris.npy',c[bad])
Fn=F[~bad]
bl=bytearray(blob)
while len(bl)%4: bl.append(0)
off=len(bl); bl.extend(Fn.astype('<u4').ravel().tobytes())
g.bufferViews.append(BufferView(buffer=0,byteOffset=off,byteLength=Fn.size*4,target=34963))
g.accessors.append(Accessor(bufferView=len(g.bufferViews)-1,componentType=5125,count=Fn.size,type='SCALAR'))
pr[0].indices=len(g.accessors)-1; g.buffers[0].byteLength=len(bl); g.set_binary_blob(bytes(bl)); g.save(dst)
