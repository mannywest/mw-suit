import sys;sys.path.insert(0,sys.argv[1])
from common import *
g,blob,P,N,U0,U1,Fs=load(sys.argv[2])
def surf_samples(T,k=6):
    # sample points on the triangles (area-uniform-ish) for a fair surface comparison
    A=P[T[:,0]];B=P[T[:,1]];C=P[T[:,2]]
    r=np.random.default_rng(0);pts=[]
    for _ in range(k):
        u=r.random((len(T),1));v=r.random((len(T),1));m=(u+v)>1;u[m]=1-u[m];v[m]=1-v[m]
        pts.append(A+u*(B-A)+v*(C-A))
    return np.vstack(pts)
def nn(a,b):
    out=np.empty(len(a))
    for i in range(0,len(a),2000):
        d=((a[i:i+2000,None,:]-b[None,:,:])**2).sum(-1);out[i:i+2000]=np.sqrt(d.min(1))
    return out
for k,name in [(1,'NOTCH'),(2,'PEAK')]:
    T=Fs[k];c=P[T].mean(1)
    front=T[(c[:,2]>0.0)]  # front part (lapels), z>0 is front
    s=surf_samples(front);L=s[s[:,0]>0.003];R=s[s[:,0]<-0.003]
    Rm=R*np.array([-1,1,1])
    d1=nn(L,Rm);d2=nn(Rm,L)
    print(f'{name}: front lapel samples L {len(L)} R {len(R)}')
    print('   mirror mismatch mm: median %.1f  90%% %.1f  max %.1f'%(np.median(np.r_[d1,d2])*1000,np.percentile(np.r_[d1,d2],90)*1000,max(d1.max(),d2.max())*1000))
    # where are the worst mismatches
    for lab,pts,d in [('left(+x)',L,d1),('right(-x, mirrored)',Rm,d2)]:
        bad=pts[d>0.008]
        if len(bad):
            print('   %s: %d samples >8mm off; height range %.0f-%.0f mm, x %.0f-%.0f, z %.0f-%.0f'%(lab,len(bad),bad[:,1].min()*1000,bad[:,1].max()*1000,bad[:,0].min()*1000,bad[:,0].max()*1000,bad[:,2].min()*1000,bad[:,2].max()*1000))
            H=np.histogram(bad[:,1],bins=np.arange(1.0,1.52,0.04))[0];print('     by height(1.00..1.52 step 40mm):',H.tolist())
    # overall extents per side
    for lab,pts in [('L',L),('R',R)]:
        print('   %s extents x %.0f..%.0f  y %.0f..%.0f  z %.0f..%.0f'%(lab,pts[:,0].min()*1000,pts[:,0].max()*1000,pts[:,1].min()*1000,pts[:,1].max()*1000,pts[:,2].min()*1000,pts[:,2].max()*1000))
