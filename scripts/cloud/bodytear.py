import sys, numpy as np
from collections import Counter
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]
# weld duplicate vertices by position (1e-5) so seam duplicates are not mistaken for tears
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
E=Counter()
for t in Fb:
    a,b,c=inv[t]
    for u,v in ((a,b),(b,c),(c,a)): E[(min(u,v),max(u,v))]+=1
rep={}
for i,k in enumerate(inv): rep.setdefault(k,i)
bd=[e for e,c in E.items() if c==1]
print('welded body open edges total',len(bd))
box=lambda p:(0.085<abs(p[0])<0.125) and 1.425<p[1]<1.452 and -0.05<p[2]<-0.01
sel=[(P[rep[a]],P[rep[b]]) for a,b in bd if box(P[rep[a]]) or box(P[rep[b]])]
print('open edges in neck-shoulder box:',len(sel))
for p,q in sorted(sel,key=lambda t:(t[0][0]>0,t[0][0]))[:40]: print(np.round(p*1000,1),np.round(q*1000,1))
