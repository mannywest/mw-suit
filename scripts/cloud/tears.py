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
box=lambda p:(0.06<abs(p[0])<0.16) and 1.40<p[1]<1.47 and -0.07<p[2]<0.0
sel=[e for e in bd if box(pos(e[0])) or box(pos(e[1]))]
# connected components of selected boundary edges
adj=defaultdict(list)
for a,b in sel: adj[a].append(b); adj[b].append(a)
seen=set(); comps=[]
for s in adj:
    if s in seen: continue
    st=[s]; comp=[]; seen.add(s)
    while st:
        v=st.pop(); comp.append(v)
        for w in adj[v]:
            if w not in seen: seen.add(w); st.append(w)
    comps.append(comp)
print('boundary edges in zone',len(sel),'components',len(comps))
for c in sorted(comps,key=lambda c:-len(c)):
    pts=np.array([pos(v) for v in c]); deg=Counter(len(adj[v]) for v in c)
    closed = all(len(adj[v])==2 for v in c)
    print('comp n=%3d closed_loop=%s degs=%s  x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f mm'%(len(c),closed,dict(deg),*(pts[:,0].min()*1000,pts[:,0].max()*1000,pts[:,1].min()*1000,pts[:,1].max()*1000,pts[:,2].min()*1000,pts[:,2].max()*1000)))
