# Base build B: rebuild the back/side neck rim as ONE clean line. input = base_stepA glb.
import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from common import load, depthmap
from scipy.ndimage import gaussian_filter1d, median_filter
src,out=sys.argv[1],sys.argv[2]
g,blob,P,N,U0,U1,Fs=load(src); jm=g.meshes[1]; pr=jm.primitives; Fb=Fs[0].copy(); ZC=-0.005; nV=len(P)
PH0,PH1=-152.0,152.0; BAND=0.004; TAP=30.0; FLOOR=0.000
# flip the 2 wrongly wound triangles at the back (dark spots)
Q=P[Fb]; n=np.cross(Q[:,1]-Q[:,0],Q[:,2]-Q[:,0]); vn=N[Fb].mean(1); c=Q.mean(1)
flip=((n*vn).sum(1)<0)&(c[:,1]>1.38)&(np.hypot(c[:,0],c[:,2]-ZC)<0.14); print('flipped winding fixed:',flip.sum()); Fb[flip]=Fb[flip][:,[0,2,1]]
r=np.hypot(P[:,0],P[:,2]-ZC); ph=np.degrees(np.arctan2(P[:,0],-(P[:,2]-ZC)))
# surface height field + rim profile
sel=Fb[(P[Fb][:,:,1].min(1)>1.25)]; x0,x1,z0,z1=-0.19,0.19,-0.12,0.09; hs=2000; W=int(.38*hs); H=int(.21*hs)
Hz,_,hs=depthmap(P[:,[0,2,1]]*[-1,1,-1],sel,(x0,x1,z0,z1),W,H)
def Hat(x,z):
    c=int((x-x0)*hs); rw=int((z1-z)*hs); return Hz[rw,c] if (0<=rw<H and 0<=c<W) else np.nan
phis=np.arange(PH0-6,PH1+6.1,2.0); rim=[]
for p in phis:
    t=np.radians(p); v=np.nan
    for rr in np.arange(0.06,0.12,0.0005):
        if np.isfinite(Hat(rr*np.sin(t),ZC-rr*np.cos(t))): v=rr; break
    rim.append(v)
rim=np.array(rim); ok=np.isfinite(rim); rim=np.interp(phis,phis[ok],rim[ok])
R=gaussian_filter1d(median_filter(rim,size=7,mode='nearest'),sigma=4,mode='nearest')   # smooth: 8 degrees
def sm(x,a,b): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
wfl=sm(np.abs(phis),85,100)*(1-sm(np.abs(phis),132,150))
R=gaussian_filter1d(np.maximum(R,FLOOR*wfl),sigma=2,mode='nearest')              # raise the rim at the front sides so the standing lip is cut away
RAW=median_filter(rim,size=3,mode='nearest')
def S_(p): return np.clip((PH1-np.abs(p))/TAP,0,1)
Rf=lambda p: np.interp(p,phis,R)*S_(p)+np.interp(p,phis,RAW)*(1-S_(p))     # ends blend back to the real rim so no gap is left
# delete the ragged rim band
cen=P[Fb].mean(1); rc=np.hypot(cen[:,0],cen[:,2]-ZC); pc=np.degrees(np.arctan2(cen[:,0],-(cen[:,2]-ZC)))
dele=(cen[:,1]>1.38)&(pc>PH0)&(pc<PH1)&(rc<Rf(pc)+BAND*S_(pc))&(rc<0.13)
print('rim triangles deleted:',dele.sum())
keep=Fb[~dele]; gone=Fb[dele]
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
def edges(F): T=inv[F]; return np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1)
Ek=edges(keep); Eg=edges(gone)
sk=set(map(tuple,Ek)); bd=[e for e in map(tuple,np.unique(Eg,axis=0)) if e in sk]          # edges shared by deleted and kept
wv=np.unique(np.array(bd).ravel()) if bd else np.array([],int)
rep={}
for t in keep:
    for v in t: rep.setdefault(inv[v],v)
Bv=np.array([rep[w] for w in wv if w in rep]); Bp=P[Bv]
rb=np.hypot(Bp[:,0],Bp[:,2]-ZC); pb=np.degrees(np.arctan2(Bp[:,0],-(Bp[:,2]-ZC)))
m=(pb>PH0-3)&(pb<PH1+3)&(rb<0.13); Bv=Bv[m]; Bp=Bp[m]; pb=pb[m]; rb=rb[m]; o=np.argsort(pb); Bv=Bv[o]; Bp=Bp[o]; pb=pb[o]; rb=rb[o]
print('outer chain vertices:',len(Bv),'phi %.0f..%.0f, radius above target: mean %.1f max %.1f mm'%(pb.min(),pb.max(),(rb-Rf(pb)).mean()*1000,(rb-Rf(pb)).max()*1000))
# ring of new vertices exactly on the smooth curve
ring_ph=np.arange(pb.min(),pb.max()+0.01,1.5); Rr=Rf(ring_ph)
ry=np.array([Hat(rr*np.sin(np.radians(p)),ZC-rr*np.cos(np.radians(p))) for rr,p in zip(Rr,ring_ph)])
# fallback for NaN: use chain heights
yb=np.interp(ring_ph,pb,Bp[:,1]); ry=np.where(np.isfinite(ry),ry,yb)
ry=gaussian_filter1d(ry,sigma=1.5,mode='nearest')
RP=np.c_[Rr*np.sin(np.radians(ring_ph)),ry,ZC-Rr*np.cos(np.radians(ring_ph))]
# attributes from local affine fits
Vall=np.unique(keep.ravel()); base=len(P); newN=[];newU0=[];newU1=[]
for q in RP:
    d=np.linalg.norm(P[Vall]-q,axis=1); nb=Vall[np.argsort(d)[:18]]; M=np.c_[P[nb],np.ones(len(nb))]
    newU0.append(np.r_[q,1]@np.linalg.lstsq(M,U0[nb],rcond=None)[0]); newU1.append(np.r_[q,1]@np.linalg.lstsq(M,U1[nb],rcond=None)[0])
    nn=N[nb[:3]].mean(0); newN.append(nn/np.linalg.norm(nn))
# zipper between ring (index base+i) and chain (Bv)
tri=[]; i=0; j=0; nr=len(RP); nc=len(Bv)
while i<nr-1 or j<nc-1:
    if i<nr-1 and (j>=nc-1 or ring_ph[i+1]<=pb[j+1]): tri.append([base+i,base+i+1,Bv[j]]); i+=1
    else: tri.append([base+i,Bv[j+1],Bv[j]]); j+=1
tri=np.array(tri)
Pall=np.vstack([P,RP]); Tq=Pall[tri]; nn=np.cross(Tq[:,1]-Tq[:,0],Tq[:,2]-Tq[:,0]); bad=nn[:,1]<0
print('strip triangles',len(tri),'| wound down (flipped to up):',bad.sum()); tri[bad]=tri[bad][:,[0,2,1]]
Fnew=np.vstack([keep,tri])
# write: append vertices to every attribute buffer, new index buffer
def append_attr(acc_idx,arr):
    global blob_b
    a=g.accessors[acc_idx]; bv=g.bufferViews[a.bufferView]; n_old=a.count; w=arr.shape[1]*4
    return a,bv
buf=bytearray(g.binary_blob())
atts=pr[0].attributes
def place(name,arr):
    a=g.accessors[getattr(atts,name)]; bv=g.bufferViews[a.bufferView]; off=(bv.byteOffset or 0)+(a.byteOffset or 0); return a,bv,off
# vertex buffers are shared: add new bufferViews at the end of the blob instead
def new_view(arr,target=34962):
    global buf
    from pygltflib import BufferView, Accessor
    while len(buf)%4: buf.append(0)
    b=arr.astype('<f4').tobytes(); bo=len(buf); buf+=b
    g.bufferViews.append(BufferView(buffer=0,byteOffset=bo,byteLength=len(b),target=target)); return len(g.bufferViews)-1
# simplest safe route: rebuild the 4 attribute arrays in full as new views
from pygltflib import Accessor
def full(name,old,new):
    a=g.accessors[getattr(atts,name)]; arr=np.vstack([old,new]); bvi=new_view(arr)
    na=Accessor(bufferView=bvi,byteOffset=0,componentType=5126,count=len(arr),type={3:'VEC3',2:'VEC2'}[arr.shape[1]])
    if name=='POSITION': na.min=arr.min(0).tolist(); na.max=arr.max(0).tolist()
    g.accessors.append(na); return len(g.accessors)-1
ids={}
ids['POSITION']=full('POSITION',P,RP); ids['NORMAL']=full('NORMAL',N,np.array(newN)); ids['TEXCOORD_0']=full('TEXCOORD_0',U0,np.array(newU0)); ids['TEXCOORD_1']=full('TEXCOORD_1',U1,np.array(newU1))
# other primitives use the same attribute accessors: point every primitive at the new ones (extra vertices are unused by them)
for p in jm.primitives:
    for k,v in ids.items(): setattr(p.attributes,k,v)
other=[a for a in dir(atts) if a.startswith('COLOR') or a.startswith('JOINTS') or a.startswith('WEIGHTS')]
assert all(getattr(atts,k) is None for k in other), other
from pygltflib import Accessor as A
idx=Fnew.astype('<u4').ravel(); b=idx.tobytes()
while len(buf)%4: buf.append(0)
bo=len(buf); buf+=b
from pygltflib import BufferView
g.bufferViews.append(BufferView(buffer=0,byteOffset=bo,byteLength=len(b),target=34963))
g.accessors.append(A(bufferView=len(g.bufferViews)-1,byteOffset=0,componentType=5125,count=len(idx),type='SCALAR',min=[int(idx.min())],max=[int(idx.max())]))
pr[0].indices=len(g.accessors)-1
g.buffers[0].byteLength=len(buf); g.set_binary_blob(bytes(buf)); g.save(out); print('saved',out,'new verts',len(RP),'body tris',len(Fnew))
