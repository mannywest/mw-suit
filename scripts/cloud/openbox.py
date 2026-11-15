import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); F=Fs[0]
x0,x1,y0,y1,z0,z1=[float(v) for v in sys.argv[2:8]]
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
T=inv[F]; E=np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1); u,c=np.unique(E,axis=0,return_counts=True); op=u[c==1]
rep={}
for i,p in enumerate(P): rep.setdefault(inv[i],(i,p))
for a,b in op:
    A=rep[a][1]*1000; B=rep[b][1]*1000; M=(A+B)/2
    if x0<=M[0]<=x1 and y0<=M[1]<=y1 and z0<=M[2]<=z1: print(rep[a][0],rep[b][0],np.round(A,1).tolist(),np.round(B,1).tolist())
