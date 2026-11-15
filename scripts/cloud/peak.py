import trimesh,numpy as np,json,sys
sys.path.insert(0,'.')
from rast import render
s=trimesh.load('s7/pkg6/public/models/MW_Tailleur_suit_repaired_v2.glb',process=False)
g=s.geometry['Jacket'];V0=np.array(g.vertices,float);F=np.array(g.faces);N0=np.array(g.vertex_normals,float)
fl=np.load('jl.npy')
sel=np.zeros(len(F),bool);sel[json.load(open('lapcol_tris2.json'))]=True
lapisl=np.isin(fl,np.load('lapsel.npy'));colisl=np.isin(fl,np.load('colsel.npy'))
lapF=sel&lapisl;colF=sel&colisl&~lapisl
P=dict(cx=0.143,cy=1.391,R=0.065,dx=0.022,dy=0.034,cut=0.088,zoff=0.004)
if len(sys.argv)>1: P.update(json.loads(sys.argv[1]))
V=V0.copy()
T=V0[F]
nonsel=~sel
def body_z(x,y):
    idx=np.where(nonsel)[0]
    t=T[idx]
    a,b,c=t[:,0,:2],t[:,1,:2],t[:,2,:2];p=np.array([x,y])
    d=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);d=np.where(abs(d)<1e-12,1e-12,d)
    u=((b[:,1]-c[:,1])*(p[0]-c[:,0])+(c[:,0]-b[:,0])*(p[1]-c[:,1]))/d
    v=((c[:,1]-a[:,1])*(p[0]-c[:,0])+(a[:,0]-c[:,0])*(p[1]-c[:,1]))/d
    w=1-u-v;m=(u>=0)&(v>=0)&(w>=0)
    if not m.any(): return None
    z=u[m]*t[m,0,2]+v[m]*t[m,1,2]+w[m]*t[m,2,2]
    return z.max()
lapv=np.unique(F[lapF].ravel())
moved={}
for vi in lapv:
    x,y,z=V0[vi];sg=np.sign(x) if x!=0 else 1;a=abs(x)
    d=np.hypot(a-P['cx'],(y-P['cy'])*1.0)
    if d>=P['R'] or y<1.34: continue
    w=(1-d/P['R']);w=w*w*(3-2*w)
    nx=sg*(a+P['dx']*w);ny=y+P['dy']*w
    bz=body_z(nx,ny)
    nz=z if bz is None else max(z, bz+P['zoff'])
    V[vi]=[nx,ny,nz];moved[int(vi)]=1
# cut collar fall tips
cc=V0[F].mean(1)
drop=colF&(abs(cc[:,0])>P['cut'])&(cc[:,1]<1.45)
keep=np.ones(len(F),bool);keep[drop]=False
print('moved',len(moved),'dropped',drop.sum())
col=np.tile(np.array([[150,160,200]]),(len(F),1));col[colF]=[70,190,90];col[lapF]=[230,70,70]
if __name__=='__main__':
    Fk=F[keep]
    render(V,Fk,col[keep],view='front',box=(-0.24,0.24,1.25,1.5),W=900,H=600).save('p_front.png')
    render(V,Fk,None,view='front',box=(-0.24,0.24,1.25,1.5),W=900,H=600).save('p_front_plain.png')
    json.dump({'moved':{int(i):V[i].tolist() for i in moved},'drop':np.where(drop)[0].tolist()},open('peak_edit.json','w'))
