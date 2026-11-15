import sys;sys.path.insert(0,sys.argv[1])
from common import *
g,blob,P,N,U0,U1,Fs=load(sys.argv[2])
BOX=(-0.18,0.18,1.36,1.50);W=1440;H=560
k=int(sys.argv[3]) # which lapel prim 1 or 2
F=np.vstack([Fs[0],Fs[k]]);nb=len(Fs[0])
z,fid,s=depthmap(P,F,BOX,W,H)
emp=~np.isfinite(z)
# hole = empty pixel with filled pixels both above and below in column
for c in range(0,W,1):
    col=emp[:,c];f=np.where(~col)[0]
    if len(f)==0: continue
    top=f.min();bot=f.max()
    holes=np.where(col[top:bot])[0]+top
    if len(holes):
        x=-(BOX[0]+(c+.5)/s)
        if c%8==0: print('x %6.1f mm  hole rows y(mm) %s'%(x*1000, [round((BOX[3]-(r+.5)/s)*1000,1) for r in holes[[0,-1]]]), 'n',len(holes))
