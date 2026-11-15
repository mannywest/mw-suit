import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1])
for k,F in enumerate(Fs):
    Q=P[F]; c=Q.mean(1); r=np.hypot(c[:,0],c[:,2]+0.005); phi=np.degrees(np.arctan2(c[:,0],-(c[:,2]+0.005)))
    m=(r<0.072)&(c[:,1]>1.40)
    print('prim',k,'tris inside r<72mm above y1.40:',m.sum())
    for t in np.where(m)[0][:12]:
        print('  ',np.round(Q[t]*1000).astype(int).tolist(), 'phi %.0f r %.0f'%(phi[t],r[t]*1000))
