import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
B=(-0.19,0.19,-0.12,0.09); W=760; H=420
def hf(f):
    g,blob,P,N,U0,U1,Fs=load(f); Fb=Fs[0]; sel=Fb[(P[Fb][:,:,1].min(1)>1.30)]
    return depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,B,W,H)[0]
a=hf(sys.argv[1]); b=hf(sys.argv[2])
both=np.isfinite(a)&np.isfinite(b); d=(b-a)[both]
print('cells where body existed before: patch/new geometry raises the surface by max %.3f mm, lowers by max %.3f mm'%(d.max()*1000,d.min()*1000))
newc=(~np.isfinite(a))&np.isfinite(b); print('cells newly covered: %d (%.1f mm2)'%(newc.sum(),newc.sum()*(1000/(W/0.38))**2))
