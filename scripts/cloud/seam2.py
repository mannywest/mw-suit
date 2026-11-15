import numpy as np,sys
from pygltflib import GLTF2
def load(path,accid=13):
    g=GLTF2().load(path);acc=g.accessors[accid];bv=g.bufferViews[acc.bufferView]
    blob=bytearray(g.binary_blob());off=(bv.byteOffset or 0)+(acc.byteOffset or 0);n=acc.count;st=bv.byteStride
    arr=np.frombuffer(blob,dtype=np.uint8);idx=off+np.arange(n)[:,None]*st+np.arange(12)[None,:]
    P=arr[idx].copy().view('<f4').reshape(n,3).astype(float)
    return g,acc,blob,idx,P
def tris(g,accid):
    a=g.accessors[accid];bv=g.bufferViews[a.bufferView];blob=g.binary_blob()
    off=(bv.byteOffset or 0)+(a.byteOffset or 0)
    dt={5123:'<u2',5125:'<u4'}[a.componentType]
    return np.frombuffer(blob,dtype=dt,count=a.count,offset=off).reshape(-1,3).astype(int)
def seam(P,Tpk):
    from collections import Counter
    E=Counter()
    for t in Tpk:
        for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])): E[tuple(sorted((a,b)))]+=1
    bd=[e for e,c in E.items() if c==1]
    vs=set()
    for a,b in bd:
        pa,pb=P[a],P[b]
        if pa[2]<-0.005 and pb[2]<-0.005 and abs(pa[0])<0.15 and abs(pb[0])<0.15 and (pa[1]+pb[1])/2<1.465: vs|={a,b}
    return np.array(sorted(vs))
if __name__=='__main__':
    g,acc,blob,idx,P=load('/tmp/tr.glb')
    Tp=tris(g,11);Tp=Tp[(Tp<34307).all(1)]
    vs=seam(P,Tp);B=P[vs];o=np.argsort(B[:,0])
    print(len(vs));
    for p in B[o][::4]: print(np.round(p,4))
