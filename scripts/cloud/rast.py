import numpy as np
from PIL import Image
def render(V,F,col=None,view='front',box=None,W=900,H=900,light=(0.35,0.5,0.8),N=None,bg=(235,235,235)):
    """orthographic z-buffer. view: front(+z toward cam), back, left, right, top. box=(xmin,xmax,ymin,ymax) in view plane coords (u,v)."""
    V=np.asarray(V,float);F=np.asarray(F)
    R={'front':np.array([[1,0,0],[0,1,0],[0,0,1]]),
       'back':np.array([[-1,0,0],[0,1,0],[0,0,-1]]),
       'right':np.array([[0,0,-1],[0,1,0],[1,0,0]]),   # looking from +x
       'left':np.array([[0,0,1],[0,1,0],[-1,0,0]]),
       'top':np.array([[1,0,0],[0,0,-1],[0,1,0]])}[view]
    P=V@R.T   # u=x, v=y, depth=z (toward camera)
    if box is None: box=(P[:,0].min(),P[:,0].max(),P[:,1].min(),P[:,1].max())
    u0,u1,v0,v1=box
    s=min(W/(u1-u0),H/(v1-v0))
    X=(P[:,0]-u0)*s; Y=(v1-P[:,1])*s; Z=P[:,2]
    fn=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]);fn/=np.linalg.norm(fn,axis=1,keepdims=True)+1e-12
    fnr=fn@R.T
    L=np.array(light);L/=np.linalg.norm(L)
    shade=np.abs(fnr@L)*0.75+0.25
    if col is None: col=np.tile(np.array([[120,130,170]]),(len(F),1))
    col=np.asarray(col,float)
    img=np.zeros((H,W,3),np.float32);img[:]=bg
    zb=np.full((H,W),-1e9,np.float32)
    for i,f in enumerate(F):
        x=X[f];y=Y[f];z=Z[f]
        xmn=int(max(0,np.floor(x.min())));xmx=int(min(W-1,np.ceil(x.max())))
        ymn=int(max(0,np.floor(y.min())));ymx=int(min(H-1,np.ceil(y.max())))
        if xmn>xmx or ymn>ymx: continue
        d=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(d)<1e-9: continue
        gx,gy=np.meshgrid(np.arange(xmn,xmx+1)+.5,np.arange(ymn,ymx+1)+.5)
        a=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/d
        b=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/d
        c=1-a-b
        m=(a>=-1e-4)&(b>=-1e-4)&(c>=-1e-4)
        if not m.any(): continue
        zz=a*z[0]+b*z[1]+c*z[2]
        sub=zb[ymn:ymx+1,xmn:xmx+1]
        up=m&(zz>sub)
        sub[up]=zz[up]
        img[ymn:ymx+1,xmn:xmx+1][up]=col[i]*shade[i]
    return Image.fromarray(np.clip(img,0,255).astype(np.uint8))
