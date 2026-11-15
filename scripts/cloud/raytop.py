import bpy, sys
from mathutils import Vector
src=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
J=bpy.data.objects['Jacket']; dg=bpy.context.evaluated_depsgraph_get()
import numpy as np
for x in (0.0,0.02,-0.02,0.04):
    prev=None; out=[]
    for yb in np.arange(-0.30,0.30,0.002):
        ok,loc,nrm,idx,ob,mat=bpy.context.scene.ray_cast(dg,Vector((x,yb,3.0)),Vector((0,0,-1)))
        hit=ok and ob.name=='Jacket'
        if hit!=prev: out.append((round(yb*1000),'hit z=%.0f mm'%(loc.z*1000) if hit else 'miss')); prev=hit
    print('x=%d mm:'%(x*1000),out)
