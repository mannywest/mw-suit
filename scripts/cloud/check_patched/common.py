import numpy as np,sys
sys.path.insert(0,'/home/claude/mw-suit/scripts')
from pygltflib import GLTF2
from seam5 import rd
from seam2 import tris
def depthmap(P,F,view_box,W,H):
    """back view: u=-x, v=y, depth d=-z (bigger = closer to camera). returns depth (nan where empty) and face id"""
    u0,u1,v0,v1=view_box;s=W/(u1-u0)
    X=(-P[:,0]-u0)*s;Y=(v1-P[:,1])*s;Z=-P[:,2]
    zb=np.full((H,W),-np.inf);fid=np.full((H,W),-1)
    for i,f in enumerate(F):
        x=X[f];y=Y[f];z=Z[f]
        xmn=int(max(0,np.floor(x.min())));xmx=int(min(W-1,np.ceil(x.max())));ymn=int(max(0,np.floor(y.min())));ymx=int(min(H-1,np.ceil(y.max())))
        if xmn>xmx or ymn>ymx: continue
        d=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(d)<1e-12: continue
        gx,gy=np.meshgrid(np.arange(xmn,xmx+1)+.5,np.arange(ymn,ymx+1)+.5)
        a=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/d;b=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/d;c=1-a-b
        m=(a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)
        if not m.any(): continue
        zz=a*z[0]+b*z[1]+c*z[2];sub=zb[ymn:ymx+1,xmn:xmx+1];fs=fid[ymn:ymx+1,xmn:xmx+1];up=m&(zz>sub);sub[up]=zz[up];fs[up]=i
    return zb,fid,s
def load(f):
    g=GLTF2().load(f);blob=g.binary_blob();pr=g.meshes[1].primitives;a=pr[0].attributes
    P=rd(g,blob,a.POSITION,3);N=rd(g,blob,a.NORMAL,3);U0=rd(g,blob,a.TEXCOORD_0,2);U1=rd(g,blob,a.TEXCOORD_1,2)
    Fs=[tris(g,p.indices) for p in pr]
    return g,blob,P,N,U0,U1,Fs
