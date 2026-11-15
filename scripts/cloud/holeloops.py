import sys, numpy as np
from collections import Counter, defaultdict
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
rep={}
for i,k in enumerate(inv): rep.setdefault(k,i)
E=Counter()
for t in Fb:
    a,b,c=inv[t]
    for u,v in ((a,b),(b,c),(c,a)): E[(min(u,v),max(u,v))]+=1
bd=[e for e,c in E.items() if c==1]
pos=lambda k:P[rep[k]]
for name,(xa,xb,za,zb) in {'right':(90.2,97.8,-32.8,-16.2),'left':(-94.2,-90.8,-31.2,-23.8)}.items():
    m=3.0
    sel=[e for e in bd if all(xa-m<=pos(v)[0]*1000<=xb+m and za-m<=pos(v)[2]*1000<=zb+m and 1.42<pos(v)[1]<1.47 for v in e)]
    adj=defaultdict(list)
    for a,b in sel: adj[a].append(b); adj[b].append(a)
    print(name,'edges',len(sel),'degrees',Counter(len(v) for v in adj.values()))
    # walk loop from any node
    if all(len(v)==2 for v in adj.values()) and sel:
        s=next(iter(adj)); loop=[s]; prev=None; cur=s
        while True:
            nx=[w for w in adj[cur] if w!=prev]; 
            nxt=nx[0] if nx else None
            if nxt is None or nxt==s: break
            loop.append(nxt); prev,cur=cur,nxt
        print('  closed loop of',len(loop),'vertices')
        for v in loop: print('   ',np.round(pos(v)*1000,1))
