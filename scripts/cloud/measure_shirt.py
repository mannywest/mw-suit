import sys, numpy as np
sys.path.insert(0,'/home/claude/work/scripts/check'); sys.path.insert(0,'/home/claude/work/scripts')
from pygltflib import GLTF2
from seam5 import rd
from seam2 import tris
g=GLTF2().load('/home/claude/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb'); blob=g.binary_blob()
print([ (i,m.name,[g.materials[p.material].name for p in m.primitives]) for i,m in enumerate(g.meshes)])
zc0=-0.005
for i,m in enumerate(g.meshes):
    if m.name in ('Shirt','Tie','Waistcoat'):
        p=m.primitives[0]; P=rd(g,blob,p.attributes.POSITION,3)
        F=tris(g,p.indices); V=np.unique(F.ravel()); P=P[V]
        top=P[:,1].max(); print(m.name,'y max %.3f'%top,'bbox',P.min(0).round(3),P.max(0).round(3))
        if m.name=='Shirt':
            m_=P[:,1]>1.38; Q=P[m_]; phi=np.degrees(np.arctan2(Q[:,0],-(Q[:,2]-zc0))); r=np.hypot(Q[:,0],Q[:,2]-zc0)
            for lo in range(-180,181,30):
                s=(phi>=lo)&(phi<lo+30)
                if s.any(): 
                    j=np.argsort(-Q[s,1])[:max(3,s.sum()//10)]
                    print(' phi %4d..%4d n%4d y %.3f..%.3f  r %.3f..%.3f  top-verts r %.3f y %.3f'%(lo,lo+30,s.sum(),Q[s,1].min(),Q[s,1].max(),r[s].min(),r[s].max(),r[s][j].mean(),Q[s][j,1].mean()))
