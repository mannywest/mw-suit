import bpy, math, sys
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
src,prefix,hide_mat=argv[0],argv[1],argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc=bpy.context.scene
for o in bpy.data.objects:
    if o.type=='MESH' and o.name!='Jacket': o.hide_render=True
J=bpy.data.objects['Jacket']
if hide_mat:
    import bmesh
    me=J.data;bm=bmesh.new();bm.from_mesh(me)
    idx=[i for i,m in enumerate(me.materials) if m.name==hide_mat][0]
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==idx],context='FACES');bm.to_mesh(me)
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.9,0.9,0.9,1)
L=bpy.data.lights.new("Sun",'SUN'); L.energy=3
lo=bpy.data.objects.new("Sun",L); sc.collection.objects.link(lo); lo.rotation_euler=(math.radians(40),0,math.radians(20))
cd=bpy.data.cameras.new("Cam"); cd.type='ORTHO'
cam=bpy.data.objects.new("Cam",cd); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=16; sc.cycles.use_denoising=False
sc.render.resolution_x=800; sc.render.resolution_y=900
views={'front':((0,-1,0),(0,0,1.30),0.50),'front34':((0.7,-1,0.2),(0,0,1.30),0.50),'frontclose':((0,-1,0.15),(0.07,0,1.36),0.22)}
for k,(d,t,s) in views.items():
    d=Vector(d).normalized();t=Vector(t)
    cam.location=t+d*1.0; cd.ortho_scale=s
    cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=prefix+'_'+k+'.png'
    bpy.ops.render.render(write_still=True)
