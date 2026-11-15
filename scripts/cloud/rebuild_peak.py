import numpy as np,json,sys
sys.argv=['x','{"dx":0.03,"dy":0.016,"R":0.075,"cut":0.075}']
exec(open('peak.py').read().split("if __name__")[0])
A=np.load('jacket_attrs.npz');UV0=A['TEXCOORD_0'];UV1=A['TEXCOORD_1']
cfg=dict(R0=0.010,off=0.003,Nu=30,Nv=10,rim=0.004,Tx=0.157,Ty=1.426,Hx=0.085,Hy=1.401,Cx=0.137,Cy=1.412,Gy=1.445,Gx=0.063,B0y=1.115,B0x=0.019,under=0.004)
if len(sys.argv)>2: cfg.update(json.loads(sys.argv[2]))
crest={}
def shoulder_top(x):
    m=(abs(abs(V0[:,0])-x)<0.004)&(~np.isin(np.arange(len(V0)),np.unique(F[sel].ravel())))
    return V0[m,1].max() if m.any() else 9
cfg['Ty']=min(cfg['Ty'],shoulder_top(cfg['Tx'])-0.004)
print('Tip y',round(cfg['Ty'],4),'shoulder crest at tip x',round(shoulder_top(cfg['Tx']),4))
# smooth outline curves (left-side magnitudes)
ys=np.array([1.14,1.16,1.18,1.20,1.22,1.24,1.26,1.28,1.30,1.32,1.34,1.36,1.38])
xo=np.array([0.035,0.051,0.062,0.072,0.080,0.092,0.102,0.109,0.116,0.125,0.129,0.137,0.144])
yi=np.array([1.14,1.18,1.22,1.26,1.30,1.34,1.38,1.42,1.44]);xi=np.array([0.019,0.021,0.029,0.036,0.045,0.053,0.058,0.061,0.063])
po=np.polyfit(ys,xo,3);pi_=np.polyfit(yi,xi,3)
def outer_x(y): return np.polyval(po,y)
def inner_x(y): return np.polyval(pi_,y)
# curve A: B0 -> G ; curve B: B0 -> corner (y 1.38) then straight to T
def curve(f,y0,y1,n): yy=np.linspace(y0,y1,n);return np.c_[f(yy),yy]
def arc(P): d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))];return d/d[-1]
def resample(P,n):
    s=arc(P);t=np.linspace(0,1,n);return np.c_[np.interp(t,s,P[:,0]),np.interp(t,s,P[:,1])]
B0=np.array([cfg['B0x'],cfg['B0y']]);G=np.array([cfg['Gx'],cfg['Gy']]);Tp=np.array([cfg['Tx'],cfg['Ty']])
Acurve=np.vstack([B0,curve(inner_x,1.14,cfg['Gy'],60)]);Acurve[-1]=G
Bpts=np.vstack([B0,curve(outer_x,1.14,1.38,50),[0.1445,1.39],Tp])
# polyline top: G->H->C->T
top=np.array([G,[cfg['Hx'],cfg['Hy']],[cfg['Cx'],cfg['Cy']],Tp])
Nu,Nv=cfg['Nu'],cfg['Nv']
Au=resample(Acurve,Nu+1);Bu=resample(Bpts,Nu+1);Tv=resample(top,Nv+1)   # Tv from G (v=0) to T (v=1)
# Coons patch with degenerate bottom (point B0): P(u,v)=(1-v)A(u)+vB(u)+u*(Tv(v)-((1-v)G+vT))
u=np.linspace(0,1,Nu+1)[:,None,None];v=np.linspace(0,1,Nv+1)[None,:,None]
Pg=(1-v)*Au[:,None,:]+v*Bu[:,None,:]+u*(Tv[None,:,:]-((1-v)*G+v*Tp))
# extend top row slightly under the collar (raise by 'under')
Pg[:,:,1]+=cfg['under']*(u[:,:,0]**4)
print('grid',Pg.shape)
# body z + roll
lt=np.where(lapF)[0];TL=V0[F[lt]]
def z_old(x,y):
    a,b,c=TL[:,0,:2],TL[:,1,:2],TL[:,2,:2];p=np.array([x,y])
    d=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);d=np.where(abs(d)<1e-12,1e-12,d)
    u=((b[:,1]-c[:,1])*(p[0]-c[:,0])+(c[:,0]-b[:,0])*(p[1]-c[:,1]))/d
    v=((c[:,1]-a[:,1])*(p[0]-c[:,0])+(a[:,0]-c[:,0])*(p[1]-c[:,1]))/d
    w=1-u-v;out=np.maximum(0,-np.minimum(np.minimum(u,v),w))
    inside=out<1e-9
    if inside.any():
        z=u[inside]*TL[inside,0,2]+v[inside]*TL[inside,1,2]+w[inside]*TL[inside,2,2];return z.max(),True
    return None,False
def bz_fill(P):
    out=np.zeros(len(P));src=np.zeros(len(P),int)
    for i,(x,y) in enumerate(P):
        z,ins=z_old(-x,y)
        if ins: out[i]=z;src[i]=1;continue
        z=body_z(-x,y)
        out[i]=np.nan if z is None else z
    return out
flat=Pg.reshape(-1,2);bz=bz_fill(flat)
ok=~np.isnan(bz)
if (~ok).any():
    from scipy.interpolate import NearestNDInterpolator
    bz[~ok]=NearestNDInterpolator(flat[ok],bz[ok])(flat[~ok])
print('grid pts without body',(~ok).sum(),'of',len(ok))
bz=bz.reshape(Nu+1,Nv+1)
from scipy.ndimage import median_filter,gaussian_filter
bz=gaussian_filter(bz,sigma=(1.0,0.7),mode='nearest')
vv=np.linspace(0,1,Nv+1)[None,:];uu=np.linspace(0,1,Nu+1)[:,None]
s=np.clip(uu/0.25,0,1);s=s*s*(3-2*s)*0.6+0.4*np.ones_like(uu)*0+0.0
s=0.35+0.65*np.clip(uu/0.3,0,1)
roll=cfg['off']+cfg['R0']*s*np.sin(np.pi*vv)**1.0*(1-0.3*vv)
# v here runs along the TOP polyline direction at u=1 only; across-width param is v for all u (inner v=0 -> outer v=1)
Z=bz+roll
Pl=np.dstack([-Pg[:,:,0],Pg[:,:,1],Z])   # left side (x negative)
# --- UV: affine fit of TEXCOORD_1 / TEXCOORD_0 to (x,y) from lapel verts, per side
def fit(side,uvA):
    best=None
    for isl in np.unique(fl[lapF]):
        tm=lapF&(fl==isl);lv=np.unique(F[tm].ravel());lv=lv[np.sign(V0[lv,0])==side]
        if len(lv)<30: continue
        M=np.c_[V0[lv,0],V0[lv,1],np.ones(len(lv))]
        co,*_=np.linalg.lstsq(M,uvA[lv],rcond=None);r=np.linalg.norm(M@co-uvA[lv],axis=1)
        if best is None or len(lv)>best[3]: best=(co,np.median(r),r.max(),len(lv),isl)
    return best
sides={}
for side,flip in ((-1,1),(1,-1)):
    b1=fit(side,UV1);b0=fit(side,UV0)
    print('side',side,'UV1 island',b1[4],'verts',b1[3],'resid med %.4f max %.4f'%(b1[1],b1[2]),'| UV0 island',b0[4],'resid med %.4f'%b0[1])
    sides[side]=(b1[0],b0[0])
def build(side):
    P=Pl.copy()
    if side==1: P[:,:,0]*=-1
    flat=P.reshape(-1,3)
    M=np.c_[flat[:,0],flat[:,1],np.ones(len(flat))]
    c1,c0=sides[side]
    return flat,M@c1,M@c0
verts=[];nrm=[];uv0=[];uv1=[];tris=[]
def quadidx(base,flip):
    for i in range(Nu):
        for j in range(Nv):
            a=base+i*(Nv+1)+j;b=a+1;c=a+(Nv+1);d=c+1
            tris.extend(([a,c,b],[b,c,d]) if not flip else ([a,b,c],[b,d,c]))
def tri_normals(P,T):
    P=np.asarray(P);T=np.asarray(T);fn=np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]]);n=np.zeros_like(P)
    for k in range(3): np.add.at(n,T[:,k],fn)
    return n/(np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
out_tris=[];out_P=[];out_N=[];out_U0=[];out_U1=[]
for side in (-1,1):
    flat,u1,u0=build(side);base=sum(len(p) for p in out_P)
    tris=[];quadidx(0,False)
    T=np.array(tris)
    N=tri_normals(flat,T)
    # orient so normals point +z (front)
    if N[:,2].mean()<0: T=T[:,[0,2,1]];N=-N
    # rim along outer edge (v=1 column) and peak part of top edge (u=1, from C to T): approximate: outer column + top row segment for v>=0.66
    rimP=[];rimT=[];rimU0=[];rimU1=[]
    def add_rim(idxs):
        k0=len(flat)+len(rimP)
        for ii in idxs: rimP.append(flat[ii]-N[ii]*cfg['rim']);rimU0.append(u0[ii]);rimU1.append(u1[ii])
        for q in range(len(idxs)-1):
            a,b=idxs[q],idxs[q+1];a2,b2=k0+q,k0+q+1
            rimT.append([a,b,b2]);rimT.append([a,b2,a2])
    col_outer=[i*(Nv+1)+Nv for i in range(Nu+1)]
    add_rim(col_outer)
    v0=int(round(Nv*0.66));top_row=[Nu*(Nv+1)+j for j in range(v0,Nv+1)][::-1]  # from T inward
    add_rim(top_row)
    rimT=np.array(rimT)
    # orient rim normals outward: test with centroid direction
    Pall=np.vstack([flat,np.array(rimP)])
    cen=flat.mean(0)
    rn=np.cross(Pall[rimT[:,1]]-Pall[rimT[:,0]],Pall[rimT[:,2]]-Pall[rimT[:,0]]);rc=Pall[rimT].mean(1)
    flip=((rc[:,:2]-cen[:2])*rn[:,:2]).sum(1)<0
    rimT[flip]=rimT[flip][:,[0,2,1]]
    allT=np.vstack([T,rimT]);Nall=tri_normals(Pall,allT)
    out_tris.append(allT+base);out_P.append(Pall);out_N.append(Nall)
    out_U0.append(np.vstack([u0,np.array(rimU0)]));out_U1.append(np.vstack([u1,np.array(rimU1)]))
    # re-index base for next
    base_next=base+len(Pall)
    # shift base accounting: since base used len(out_P) as list length -> fix below
Pv=np.vstack(out_P);Nv_=np.vstack(out_N);U0=np.vstack(out_U0);U1=np.vstack(out_U1);Tt=np.vstack(out_tris)
print('new verts',len(Pv),'new tris',len(Tt))
collar_ids=np.where(colF)[0]
json.dump({'P':Pv.tolist(),'N':Nv_.tolist(),'U0':U0.tolist(),'U1':U1.tolist(),'T':Tt.tolist(),'collar':collar_ids.tolist(),'lapel_old':np.where(lapF)[0].tolist()},open('peak_rebuild.json','w'))
# preview render (rasterizer): new lapel + collar + body
import trimesh
body=np.where(~sel)[0]
Vall=np.vstack([V0,Pv]);Fall=np.vstack([F[body],F[collar_ids],Tt+len(V0)])
colr=np.vstack([np.tile([[150,160,200]],(len(body),1)),np.tile([[70,190,90]],(len(collar_ids),1)),np.tile([[230,70,70]],(len(Tt),1))])
render(Vall,Fall,colr,view='front',box=(-0.22,0.22,1.25,1.5),W=900,H=600).save('rb_front.png')
render(Vall,Fall,colr,view='left',box=(-0.2,0.25,1.25,1.5),W=900,H=500).save('rb_side.png')
render(Vall,Fall,colr,view='back',box=(-0.22,0.22,1.3,1.5),W=900,H=500).save('rb_back.png')
