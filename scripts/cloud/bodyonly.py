import sys
from pygltflib import GLTF2
src,out=sys.argv[1],sys.argv[2]
g=GLTF2().load(src); j=next(m for m in g.meshes if m.name=='Jacket')
print([ (g.materials[p.material].name if p.material is not None else None) for p in j.primitives])
j.primitives=[p for p in j.primitives if p.material is None or g.materials[p.material].name not in('Jacket_Lapel_Peak','Jacket_Lapel')]
g.save(out); print('kept',len(j.primitives))
