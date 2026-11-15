import sys, numpy as np
from collections import Counter, defaultdict
from scipy import ndimage as ndi
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]
x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; S=2000; W=int((x1-x0)*S); H=int((z1-z0)*S)
sel_=Fb[(P[Fb][:,:,1].min(1)>1.30)]
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel_,(x0,x1,z0,z1),W,H)
emp=~np.isfinite(Hz); lab,n=ndi.label(emp)
# the two enclosed holes (not touching border), keep area 5..500 mm2
holes=[]
for k in range(1,n+1):
    m=lab==k; a=m.sum()*(1000/hs)**2; rr,cc=np.where(m)
    if a<5 or a>500 or rr.min()==0 or cc.min()==0 or rr.max()==H-1 or cc.max()==W-1: continue
    holes.append(m)
print('holes',len(holes))
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
rep={}
for i,k in enumerate(inv): rep.setdefault(k,i)
E=Counter()
for t in Fb:
    a,b,c=inv[t]
    for u,v in ((a,b),(b,c),(c,a)): E[(min(u,v),max(u,v))]+=1
bd=[e for e,c in E.items() if c==1]
pos=lambda k:P[rep[k]]
def touches(m,e,tol=3):
    md=ndi.binary_dilation(m,iterations=tol)
    for t in np.linspace(0,1,12):
        p=pos(e[0])*(1-t)+pos(e[1])*t
        c=int((p[0]-x0)*hs-.5); r=int((z1-p[2])*hs-.5)
        if 0<=r<H and 0<=c<W and md[r,c]: return True
    return False
out=[]
for hi,m in enumerate(holes):
    sel=[e for e in bd if touches(m,e)]
    adj=defaultdict(list)
    for a,b in sel: adj[a].append(b); adj[b].append(a)
    rr,cc=np.where(m)
    print('hole',hi,'centre x %.1f z %.1f mm'%((x0+cc.mean()/hs)*1000,(z1-rr.mean()/hs)*1000),'edges',len(sel),'degrees',dict(Counter(len(v) for v in adj.values())))
    ok=bool(sel) and all(len(v)==2 for v in adj.values())
    if ok:
        s=next(iter(adj)); loop=[s]; prev=None; cur=s
        while True:
            nx=[w for w in adj[cur] if w!=prev]; nxt=nx[0] if nx else None
            if nxt is None or nxt==s: break
            loop.append(nxt); prev,cur=cur,nxt
        print('  closed loop,',len(loop),'vertices; covers all selected edges:',len(loop)==len(adj))
        for v in loop: print('    ',np.round(pos(v)*1000,1))
