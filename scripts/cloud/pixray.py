# pixray.py -- src view px py [px py ...] : what does the camera ray through an image pixel hit? (uses all8's camera definitions)
import bpy, sys, math
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]; src=argv[0]; view=argv[1]; pix=[float(v) for v in argv[2:]]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
sc=bpy.context.scene; J=bpy.data.objects['Jacket']
for o in bpy.data.objects:
    if o.type=='MESH' and o.name!='Jacket': o.hide_viewport=True
views={'in34':((0.8,-1,0.3),(-0.05,0,1.30),0.25,(800,900)),'front':((0,-1,0),(0,0,1.30),0.50,(800,900)),'front34':((0.7,-1,0.2),(0,0,1.30),0.50,(800,900))}
d,t,s,(w,h)=views[view]; d=Vector(d).normalized(); t=Vector(t)
dgr=bpy.context.evaluated_depsgraph_get()
fwd=-d; up0=Vector((0,0,1)); right=fwd.cross(up0).normalized(); up=right.cross(fwd).normalized()
ppm=max(w,h)/s
for k in range(0,len(pix),2):
    px,py=pix[k],pix[k+1]; o=t+d*1.0+right*((px-w/2)/ppm)+up*((h/2-py)/ppm); o=o-fwd*0.0
    hits=[]; org=o
    for _ in range(8):
        ok,loc,nrm,idx,obj,mat=sc.ray_cast(dgr,org,fwd)
        if not ok: break
        pm=J.data.polygons[idx].material_index
        hits.append((J.data.materials[pm].name,round(loc.x*1000),round(loc.z*1000),round(-loc.y*1000),'n_toward_cam' if nrm.dot(d)>0 else 'n_away'))
        org=loc+fwd*1e-4
    print('pix',px,py,'->',hits)
