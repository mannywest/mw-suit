import numpy as np,sys
sys.path.insert(0,'.')
from seam2 import load,tris
from rast import render
W,H=840,360;BOX=(-0.14,0.14,1.38,1.5)
def target(x): return 1.438-0.008*(x/0.12)**2
def ss(t): t=np.clip(t,0,1); return t*t*(3-2*t)
def edge(P,Fb,Fc):
    F=np.vstack([Fb,Fc]);col=np.vstack([np.tile([[230,230,230]],(len(Fb),1)),np.tile([[20,20,20]],(len(Fc),1))])
    im=np.array(render(P,F,col,view='back',box=BOX,W=W,H=H,bg=(255,0,0)))
    dark=(im[:,:,0]<60)&(im[:,:,1]<60)
    s=min(W/(BOX[1]-BOX[0]),H/(BOX[3]-BOX[2]))
    xs=[];ys=[]
    for c in range(W):
        r=np.where(dark[:,c])[0]
        if len(r)==0: continue
        # the lowest dark pixel that has body (light) pixel directly below
        low=r.max()
        u=BOX[0]+(c+.5)/s; x=-u; y=BOX[3]-(low+.5)/s
        xs.append(x);ys.append(y)
    return np.array(xs),np.array(ys)
def rough(xs,ys):
    m=abs(xs)<0.11; r=ys[m]-target(xs[m]); return np.sqrt((r**2).mean()),abs(r).max()
def apply(P,xs,ys):
    m=abs(xs)<0.125
    xs,ys=xs[m],ys[m]
    d=target(xs)-ys
    # smooth delta along x (gaussian, ~6 px)
    k=np.exp(-0.5*(np.arange(-12,13)/5.0)**2);k/=k.sum()
    dp=np.pad(d,12,mode='edge');ds=np.convolve(dp,k,mode='valid')
    ysm=np.convolve(np.pad(ys,12,mode='edge'),k,mode='valid')
    x,y,z=P[:,0],P[:,1],P[:,2]
    dv=np.interp(x,xs[np.argsort(xs)],ds[np.argsort(xs)]);ye=np.interp(x,xs[np.argsort(xs)],ysm[np.argsort(xs)])
    taper=1-ss((abs(x)-0.10)/0.03);wz=ss((-z)/0.02)
    h=y-ye;w=np.where(h>=0,1-ss(h/0.03),np.exp(-(h/0.012)**2))
    sel=(abs(x)<0.13)&(y>1.37)&(y<1.5)
    Q=P.copy();Q[:,1]+=np.where(sel,dv*w*taper*wz,0);return Q
if __name__=='__main__':
    g,acc,blob,idx,P0=load('/tmp/tr.glb')
    Fb=tris(g,4);Fp=tris(g,11);Fc=Fp[(Fp<34307).all(1)]
    P=P0.copy()
    xs,ys=edge(P,Fb,Fc);print('before rms,max mm',[round(v*1000,2) for v in rough(xs,ys)])
    for it in range(4):
        P=apply(P,xs,ys);xs,ys=edge(P,Fb,Fc);print(it,'rms,max mm',[round(v*1000,2) for v in rough(xs,ys)])
    np.save('P_seam3.npy',P)
