# Base build A: body-only base; remove seam slivers at the back neck; smooth the neck rim radius (phi -125..125).
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
from scipy.ndimage import gaussian_filter1d
src,out=sys.argv[1],sys.argv[2]
g,blob,P,N,U0,U1,Fs=load(src); jm=g.meshes[1]; pr=jm.primitives
a=g.accessors[pr[0].attributes.POSITION]; bv=g.bufferViews[a.bufferView]; print('position stride',bv.byteStride,'count',a.count)
Fb=Fs[0]; ZC=-0.005
# 1) rim profile from the body surface (top-view height field)
sel=Fb[(P[Fb][:,:,1].min(1)>1.25)]; x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; hs=2000; W=int(.38*hs); H=int(.21*hs)
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,(x0,x1,z0,z1),W,H)
phis=np.arange(-135,136,3.0); rim=[]
for ph in phis:
    t=np.radians(ph); v=np.nan
    for r in np.arange(0.06,0.12,0.0005):
        x=r*np.sin(t); z=ZC-r*np.cos(t); c=int((x-x0)*hs); rw=int((z1-z)*hs)
        if 0<=rw<H and 0<=c<W and np.isfinite(Hz[rw,c]): v=r; break
    rim.append(v)
rim=np.array(rim); ok=np.isfinite(rim); rim=np.interp(phis,phis[ok],rim[ok])
from scipy.ndimage import median_filter
rim_m=median_filter(rim,size=5,mode='nearest'); R=gaussian_filter1d(rim_m,sigma=3.0,mode='nearest')   # sigma 3 samples = 9 degrees
print('rim before: min %.1f max %.1f mm | target: min %.1f max %.1f mm'%(rim.min()*1000,rim.max()*1000,R.min()*1000,R.max()*1000))
# 2) displace body vertices near the rim radially so the rim lands on the smooth curve
Vb=np.unique(Fb); Pn=P.copy(); moved=0; mx=0
x=P[:,0]; z=P[:,2]-ZC; r=np.hypot(x,z); ph=np.degrees(np.arctan2(x,-z))
for i in Vb:
    if P[i,1]<1.38 or r[i]>0.125 or abs(ph[i])>130: continue
    rr0=np.interp(ph[i],phis,rim); R0=np.interp(ph[i],phis,R); d=R0-rr0
    w=np.clip(1-(r[i]-rr0)/0.015,0,1); w=w*w*(3-2*w)
    # fade out toward the end of the phi range
    w*=np.clip((130-abs(ph[i]))/10,0,1)
    if w<=0: continue
    rn=r[i]+d*w; Pn[i,0]=rn*np.sin(np.radians(ph[i])); Pn[i,2]=ZC-rn*np.cos(np.radians(ph[i])); moved+=1; mx=max(mx,abs(d*w))
print('moved %d vertices, max shift %.1f mm'%(moved,mx*1000))
# 3) remove seam slivers (tiny steep triangles along the back-centre seam)
Q=Pn[Fb]; n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); ar=np.linalg.norm(n,axis=1)/2; c=Q.mean(1)
ny=np.abs(n[:,1])/np.maximum(2*ar,1e-12); rc=np.hypot(c[:,0],c[:,2]-ZC)
sl=(c[:,1]>1.40)&(rc<0.11)&(np.abs(c[:,0])<0.03)&(c[:,2]<-0.05)&(ar<4e-6)&(ny<0.4)
print('seam slivers removed:',sl.sum()); Fb2=Fb[~sl]
# 4) write: positions in place, body indices rewritten, lapel primitive dropped
buf=bytearray(blob); off=(bv.byteOffset or 0)+(a.byteOffset or 0)
buf[off:off+a.count*12]=Pn.astype('<f4').tobytes()
ia=g.accessors[pr[0].indices]; ibv=g.bufferViews[ia.bufferView]; ioff=(ibv.byteOffset or 0)+(ia.byteOffset or 0)
dt={5123:'<u2',5125:'<u4'}[ia.componentType]; assert len(Fb)*3==ia.count
buf[ioff:ioff+len(Fb2)*3*np.dtype(dt).itemsize]=Fb2.astype(dt).ravel().tobytes(); ia.count=len(Fb2)*3
jm.primitives=[p for p in jm.primitives if g.materials[p.material].name not in('Jacket_Lapel_Peak','Jacket_Lapel')]
g.set_binary_blob(bytes(buf)); g.save(out); print('saved',out)
