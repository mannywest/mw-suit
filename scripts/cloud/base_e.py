# Base build E: smooth the ragged top edge of the neck at the front sides by relaxing the edge vertices along the edge (no topology change).
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
src,out=sys.argv[1],sys.argv[2]; IT=int(sys.argv[3]); LAM=float(sys.argv[4]); LIM=float(sys.argv[5])
g,blob,P,N,U0,U1,Fs=load(src); jm=g.meshes[1]; pr=jm.primitives; F=Fs[0]; ZC=-0.005
key=np.round(P*1e5).astype(np.int64); uk,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
T=inv[F]; E=np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1); u,c=np.unique(E,axis=0,return_counts=True); op=u[c==1]
W=np.zeros((len(uk),3)); 
for i,p in enumerate(P): W[inv[i]]=p
r=np.hypot(W[:,0],W[:,2]-ZC); ph=np.degrees(np.arctan2(W[:,0],-(W[:,2]-ZC)))
zone=(W[:,1]>1.38)&(r<0.135)&(np.abs(ph)>88)&(np.abs(ph)<152)
nbr={}
for a,b in op:
    if zone[a] and zone[b]: nbr.setdefault(a,[]).append(b); nbr.setdefault(b,[]).append(a)
ids=[k for k,v in nbr.items() if len(v)==2]; print('edge vertices to relax:',len(ids),'of',len(nbr))
W0=W.copy(); Wn=W.copy()
for _ in range(IT):
    Wt=Wn.copy()
    for k in ids:
        a,b=nbr[k]; Wt[k]=Wn[k]+LAM*((Wn[a]+Wn[b])/2-Wn[k])
    d=Wt-W0; L=np.linalg.norm(d,axis=1); s=np.where(L>LIM,LIM/np.maximum(L,1e-12),1.0); Wn=W0+d*s[:,None]
mv=np.linalg.norm(Wn-W0,axis=1); print('max shift %.1f mm, mean %.2f mm'%(mv.max()*1000,mv[ids].mean()*1000))
Pn=Wn[inv]
a=g.accessors[pr[0].attributes.POSITION]; bv=g.bufferViews[a.bufferView]; off=(bv.byteOffset or 0)+(a.byteOffset or 0)
buf=bytearray(g.binary_blob()); buf[off:off+a.count*12]=Pn.astype('<f4').tobytes(); g.set_binary_blob(bytes(buf)); g.save(out)
