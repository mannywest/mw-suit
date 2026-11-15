import numpy as np,sys
sys.path.insert(0,'.')
from pygltflib import GLTF2,Accessor,BufferView
from seam3 import edge,W,H,BOX,ss
from seam2 import tris
def rd(g,blob,accid,nc):
    a=g.accessors[accid];bv=g.bufferViews[a.bufferView];off=(bv.byteOffset or 0)+(a.byteOffset or 0);st=bv.byteStride or nc*4
    arr=np.frombuffer(blob,dtype=np.uint8);idx=off+np.arange(a.count)[:,None]*st+np.arange(nc*4)[None,:]
    return arr[idx].copy().view('<f4').reshape(a.count,nc).astype(float)
def gs(a,sig):
    n=int(sig*3);k=np.exp(-0.5*(np.arange(-n,n+1)/sig)**2);k/=k.sum()
    return np.convolve(np.pad(a,n,mode='edge'),k,mode='valid')
def maxf(a,w):
    p=np.pad(a,w,mode='edge');return np.array([p[i:i+2*w+1].max() for i in range(len(a))])
def main(src,dst,margin=0.0):
    g=GLTF2().load(src);blob=g.binary_blob()
    P=rd(g,blob,13,3);Nn=rd(g,blob,14,3);U0=rd(g,blob,15,2);U1=rd(g,blob,16,2)
    n=len(P);Fb=tris(g,4);F10=tris(g,10);F11=tris(g,11)
    Fc=F11[(F11<34307).all(1)]
    xs,ys=edge(P,Fb,Fc);m=abs(xs)<0.135;o=np.argsort(xs[m]);xs,ys=xs[m][o],ys[m][o]
    c=gs(maxf(ys,14),8);c=c+max(0,(ys-c).max())+margin
    c=gs(c,6);c=c+max(0,(ys-c).max())
    # body top edge (body alone, top-most pixel per column)
    from rast import render as _r
    sc=min(W/(BOX[1]-BOX[0]),H/(BOX[3]-BOX[2]))
    im=np.array(_r(P,Fb,np.tile([[20,20,20]],(len(Fb),1)),view='back',box=BOX,W=W,H=H,bg=(255,0,0)));dk=im[:,:,0]<60
    bx=[];by=[]
    for cc in range(W):
        r=np.where(dk[:,cc])[0]
        if len(r): bx.append(-(BOX[0]+(cc+.5)/sc));by.append(BOX[3]-(r.min()+.5)/sc)
    bx=np.array(bx);by=np.array(by);o2=np.argsort(bx);bt=np.interp(xs,bx[o2],by[o2])
    K=np.minimum(c,bt-0.0005)
    K=gs(maxf(-maxf(-K,6),0),5)          # opening-style smoothing then gaussian
    K=np.maximum(K,np.minimum(ys,c)) if False else K
    K=np.where(abs(xs)<0.05,np.maximum(K,ys+0.0003),K);K=gs(K,3)
    print('K vs body top mm (min,max):',((bt-K).min()*1000).round(2),((bt-K).max()*1000).round(2),'K vs collar-bottom ys mm (min,max):',((K-ys).min()*1000).round(2),((K-ys).max()*1000).round(2))
    cf=lambda x:np.interp(x,xs,K)
    print('curve mm above visible seam: mean %.2f max %.2f'%(((c-ys).mean())*1000,((c-ys).max())*1000))
    newP=[];newN=[];newU0=[];newU1=[]
    def mk(a,b,t):
        newP.append(P[a]*(1-t)+P[b]*t);v=Nn[a]*(1-t)+Nn[b]*t;newN.append(v/(np.linalg.norm(v)+1e-12))
        newU0.append(U0[a]*(1-t)+U0[b]*t);newU1.append(U1[a]*(1-t)+U1[b]*t);return n+len(newP)-1
    def clip(T):
        out=[];ncut=0
        for t in T:
            pp=P[t];inreg=(abs(pp[:,0]).max()<0.128)&(pp[:,2].max()<0.0)&(pp[:,1].min()>1.37)
            if not inreg: out.append(tuple(t));continue
            gv=pp[:,1]-cf(pp[:,0])
            if (gv>=0).all(): out.append(tuple(t));continue
            if (gv<0).all(): ncut+=1;continue
            ncut+=1;poly=[]
            for i in range(3):
                a,b=t[i],t[(i+1)%3];ga,gb=gv[i],gv[(i+1)%3]
                if ga>=0: poly.append(a)
                if (ga>=0)!=(gb>=0):
                    lo,hi=0.0,1.0
                    for _ in range(30):
                        mid=(lo+hi)/2;q=P[a]*(1-mid)+P[b]*mid;gm=q[1]-cf(q[0])
                        if (gm>=0)==(ga>=0): lo=mid
                        else: hi=mid
                    poly.append(mk(a,b,(lo+hi)/2))
            for i in range(1,len(poly)-1): out.append((poly[0],poly[i],poly[i+1]))
        print('clipped tris',ncut);return np.array(out)
    # keep original order independent: rear collar tris only are altered
    N10=clip(F10);N11=clip(F11)
    def clipb(T):
        out=[];nc=0
        for t in T:
            pp=P[t];inreg=(abs(pp[:,0]).max()<0.128)&(pp[:,2].max()<0.0)&(pp[:,1].min()>1.37)
            if not inreg: out.append(tuple(t));continue
            gv=cf(pp[:,0])-pp[:,1]
            if (gv>=0).all(): out.append(tuple(t));continue
            if (gv<0).all(): nc+=1;continue
            nc+=1;poly=[]
            for i in range(3):
                a,b=t[i],t[(i+1)%3];ga,gb=gv[i],gv[(i+1)%3]
                if ga>=0: poly.append(a)
                if (ga>=0)!=(gb>=0):
                    lo,hi=0.0,1.0
                    for _ in range(30):
                        mid=(lo+hi)/2;q=P[a]*(1-mid)+P[b]*mid;gm=cf(q[0])-q[1]
                        if (gm>=0)==(ga>=0): lo=mid
                        else: hi=mid
                    poly.append(mk(a,b,(lo+hi)/2))
            for i in range(1,len(poly)-1): out.append((poly[0],poly[i],poly[i+1]))
        print('body clipped tris',nc);return np.array(out)
    N4=clipb(Fb)
    add=len(newP);print('new verts',add)
    Pn=np.vstack([P]+[np.array(newP)]) if add else P
    A=[Pn,np.vstack([Nn,np.array(newN)]),np.vstack([U0,np.array(newU0)]),np.vstack([U1,np.array(newU1)])]
    bl=bytearray(blob)
    def addacc(data,typ,ctype,target,mn=None,mx=None):
        while len(bl)%4: bl.append(0)
        off=len(bl);bl.extend(data.tobytes())
        g.bufferViews.append(BufferView(buffer=0,byteOffset=off,byteLength=len(data.tobytes()),target=target))
        g.accessors.append(Accessor(bufferView=len(g.bufferViews)-1,componentType=ctype,count=len(data),type=typ,min=mn,max=mx))
        return len(g.accessors)-1
    ids=[addacc(A[0].astype('<f4'),'VEC3',5126,34962,A[0].min(0).tolist(),A[0].max(0).tolist()),
         addacc(A[1].astype('<f4'),'VEC3',5126,34962),addacc(A[2].astype('<f4'),'VEC2',5126,34962),addacc(A[3].astype('<f4'),'VEC2',5126,34962)]
    i4=addacc(N4.astype('<u4').ravel(),'SCALAR',5125,34963);i10=addacc(N10.astype('<u4').ravel(),'SCALAR',5125,34963);i11=addacc(N11.astype('<u4').ravel(),'SCALAR',5125,34963)
    for p in g.meshes[1].primitives:
        p.attributes.POSITION,p.attributes.NORMAL,p.attributes.TEXCOORD_0,p.attributes.TEXCOORD_1=ids
        if p.indices==4:p.indices=i4
        elif p.indices==10:p.indices=i10
        elif p.indices==11:p.indices=i11
    g.buffers[0].byteLength=len(bl);g.set_binary_blob(bytes(bl));g.save(dst)
    np.save('c_curve.npy',np.c_[xs,c,ys])
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
