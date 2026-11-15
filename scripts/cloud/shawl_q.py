# quality numbers for the saved shawl grid (sh/shawl_grid.npy): penetration vs front depth (chest) and vs top height field (neck), creases by zone
import sys, numpy as np
sys.argv=['x',(sys.argv[1] if len(sys.argv)>1 else 'sh/shawl_j.glb'),'/tmp/x.glb']
src=open('/home/claude/work/scripts/shawl_step1.py').read().split('# ------------------------------------------------------------------ obstacle samples')[0]
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()): exec(src)
Cg=np.load('/home/claude/work/sh/shawl_grid.npy'); Mu1,Mv1,_=Cg.shape
# dense bilinear samples
pts=[];ij=[]
for a in np.linspace(0,1,3):
    for b in np.linspace(0,1,3):
        pts.append((Cg[:-1,:-1]*(1-a)*(1-b)+Cg[1:,:-1]*a*(1-b)+Cg[:-1,1:]*(1-a)*b+Cg[1:,1:]*a*b).reshape(-1,3))
        ii,jj=np.meshgrid(np.arange(Mu1-1),np.arange(Mv1-1),indexing='ij'); ij.append(np.c_[ii.ravel(),jj.ravel()])
pts=np.vstack(pts); ij=np.vstack(ij)
front=(pts[:,2]>0.04)&(pts[:,1]<1.42)
zb=np.where(samp(np.isfinite(zbody).astype(float),pts[:,0],pts[:,1])>0.999, samp(np.where(np.isfinite(zbody),zbody,0.0),pts[:,0],pts[:,1]), np.nan)
pen=np.where(front&np.isfinite(zb), zb-pts[:,2], np.nan)
print('CHEST: samples %d  behind body front by >0.5mm: %d  >2mm: %d  worst %.1f mm | floating >8mm above body: %d (max %.1f mm)'%(np.isfinite(pen).sum(),(pen>0.0005).sum(),(pen>0.002).sum(),np.nanmax(pen)*1000,(pen<-0.008).sum(),-np.nanmin(pen)*1000))
k=np.nanargmax(pen); print('  worst chest penetration at', np.round(pts[k]*1000).astype(int), 'grid', ij[k])
neck=(pts[:,2]<0.02)
h=hfield(pts[:,0],pts[:,2]); okn=neck&np.isfinite(h)&(h>1.30); dn=pts[:,1]-h
print('NECK : samples %d  below top surface +0.5mm: %d  min clearance %.1f mm | floating >12mm: %d'%(okn.sum(),(dn[okn]<0.0005).sum(),dn[okn].min()*1000,(dn[okn]>0.012).sum()))
n=np.cross(Cg[1:,1:]-Cg[:-1,:-1],Cg[:-1,1:]-Cg[1:,:-1]); n/=np.linalg.norm(n,axis=2,keepdims=True)+1e-12
au=np.degrees(np.arccos(np.clip((n[1:]*n[:-1]).sum(2),-1,1))); av=np.degrees(np.arccos(np.clip((n[:,1:]*n[:,:-1]).sum(2),-1,1)))
for nm,a in (('along',au),('across',av)):
    ii,jj=np.where(a>25); print('CREASE %s >25deg: %d cells; by column band:'%(nm,len(ii)), dict(zip(*np.unique((ii//20)*20,return_counts=True))))
    print('   by row j:', dict(zip(*np.unique(jj,return_counts=True))))
d=-pen[np.isfinite(pen)]*1000
print('height above front surface mm percentiles 5/25/50/75/95:',np.round(np.percentile(d,[5,25,50,75,95]),1))
m=np.isfinite(pen)&(pen>0.002); print('penetration>2mm columns:',dict(zip(*np.unique((ij[m][:,0]//10)*10,return_counts=True))), 'y range mm',np.round(pts[m][:,1].min()*1000),np.round(pts[m][:,1].max()*1000))
