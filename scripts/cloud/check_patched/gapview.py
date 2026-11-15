import sys;sys.path.insert(0,sys.argv[1])
from common import *
g,blob,P,N,U0,U1,Fs=load(sys.argv[2]);k=int(sys.argv[3]);d=np.array([float(v) for v in sys.argv[4].split(',')])
d/=np.linalg.norm(d);up=np.array([0,1,0.]);up=up-d*(up@d);up/=np.linalg.norm(up);right=np.cross(up,d)
F=np.vstack([Fs[0],Fs[k]]);nb=len(Fs[0])
tg=np.array([0,1.42,0]);Q=np.c_[-(P-tg)@right,(P-tg)@up,-(P-tg)@d]   # depthmap() uses u=-x, depth=-z
z,fid,s=depthmap(Q,F,(-0.18,0.18,-0.06,0.06),1440,480)
emp=~np.isfinite(z);H,W=emp.shape
hits=[]
for c in range(W):
    f=np.where(~emp[:,c])[0]
    if len(f)==0: continue
    h=np.where(emp[f.min():f.max(),c])[0]+f.min()
    for r in h:
        # which faces surround the hole: look up/down
        up_=fid[:r,c][fid[:r,c]>=0];dn=fid[r:,c][fid[r:,c]>=0]
        hits.append((c,r,up_[-1] if len(up_) else -1,dn[0] if len(dn) else -1))
print('hole pixels',len(hits))
F_all=F
from collections import Counter
cnt=Counter()
for c,r,a,b in hits: cnt[(int(a),int(b))]+=1
for (a,b),n in cnt.most_common(12):
    ca=P[F_all[a]].mean(0) if a>=0 else None;cb=P[F_all[b]].mean(0) if b>=0 else None
    print(n,'above:', 'body' if a<nb else 'collar', np.round(ca*1000,1), ' below:','body' if b<nb else 'collar',np.round(cb*1000,1))
