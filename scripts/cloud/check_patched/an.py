import numpy as np,sys
sys.path.insert(0,'/home/claude/mw-suit/scripts')
from pygltflib import GLTF2
from seam5 import rd
from seam2 import tris
from rast import render
S=sys.argv[2]
for tag,f in [('t6',sys.argv[3])]:
    g=GLTF2().load(f);blob=g.binary_blob();pr=g.meshes[1].primitives
    P=rd(g,blob,pr[0].attributes.POSITION,3)
    Fs=[tris(g,p.indices) for p in pr]
    cols=[[200,200,200],[200,40,40],[40,40,200],[40,200,40]]
    # sel rear neck region
    F=[];C=[]
    for k,(Fk,c) in enumerate(zip(Fs,cols)):
        if k==2: continue  # skip peak (overlaps notch) for one view
        F.append(Fk);C.append(np.tile([c],(len(Fk),1)))
    F=np.vstack(F);C=np.vstack(C)
    render(P,F,C,view='back',box=(-0.17,0.17,1.36,1.5),W=1020,H=420).save(f'{S}/{tag}_back_notch.png')
    F=np.vstack([Fs[0],Fs[2]]);C=np.vstack([np.tile([cols[0]],(len(Fs[0]),1)),np.tile([cols[2]],(len(Fs[2]),1))])
    render(P,F,C,view='back',box=(-0.17,0.17,1.36,1.5),W=1020,H=420).save(f'{S}/{tag}_back_peak.png')
    render(P,F,C,view='top',box=(-0.17,0.17,-0.12,0.14),W=1020,H=780).save(f'{S}/{tag}_top_peak.png')
