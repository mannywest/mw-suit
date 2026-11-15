import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check')
from common import load
g,blob,P,N,U0,U1,Fs=load(sys.argv[1]); Fb=Fs[0]
key=np.round(P*1e5).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
T=inv[Fb]; E=np.sort(np.r_[T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]],1); u,c=np.unique(E,axis=0,return_counts=True); op=u[c==1]
rep={}
for i,p in enumerate(P): rep.setdefault(inv[i],p)
A=np.array([rep[a] for a,b in op])*1000; B=np.array([rep[b] for a,b in op])*1000; M=(A+B)/2; L=np.linalg.norm(A-B,axis=1)
# classify by location
r=np.hypot(M[:,0],M[:,2]+5)
zones={'neck rim (r<100, y>1400)':(r<100)&(M[:,1]>1400),
 'shoulder/armhole (y>1330, r>=100)':(r>=100)&(M[:,1]>1330),
 'front edge (z>40, |x|<200, y 1000-1400)':(M[:,2]>40)&(np.abs(M[:,0])<200)&(M[:,1]<1400)&(M[:,1]>1000),
 'back panel mid (z<-40, y 1100-1400)':(M[:,2]<-40)&(M[:,1]>1100)&(M[:,1]<1400)}
for k,m in zones.items(): print('%-42s %4d edges, %6.0f mm'%(k,m.sum(),L[m].sum()))
m=zones['neck rim (r<100, y>1400)']
ang=np.degrees(np.arctan2(M[m,0],-(M[m,2]+5))); o=np.argsort(ang)
print('neck rim: angle (0=back centre) range %.0f..%.0f ; mean y %.0f ; y min/max %.0f/%.0f ; mean radius %.0f mm'%(ang.min(),ang.max(),M[m,1].mean(),M[m,1].min(),M[m,1].max(),r[m].mean()))
# gaps in angle coverage of the rim
a=np.sort(ang); d=np.diff(a); big=np.where(d>6)[0]
print('rim coverage gaps >6 deg:',[(round(a[i]),round(a[i+1])) for i in big])
