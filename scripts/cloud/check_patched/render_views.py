import bpy, math, sys
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
src,prefix=argv[0],argv[1]; hide_mat=argv[2] if len(argv)>2 else ''
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc=bpy.context.scene
for o in bpy.data.objects:
    if o.type=='MESH' and o.name!='Jacket': o.hide_render=True
J=bpy.data.objects['Jacket']
if hide_mat:  # delete faces of a material to show one lapel variant
    import bmesh
    me=J.data;bm=bmesh.new();bm.from_mesh(me)
    idx=[i for i,m in enumerate(me.materials) if m.name==hide_mat][0]
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==idx],context='FACES');bm.to_mesh(me)
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.9,0.9,0.9,1)
L=bpy.data.lights.new("Sun",'SUN'); L.energy=3
lo=bpy.data.objects.new("Sun",L); sc.collection.objects.link(lo); lo.rotation_euler=(math.radians(-50),0,math.radians(160))
cd=bpy.data.cameras.new("Cam"); cd.type='ORTHO'
cam=bpy.data.objects.new("Cam",cd); sc.collection.objects.link(cam); sc.camera=cam
sc.view_settings.view_transform='Filmic'; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=16; sc.cycles.use_denoising=False
sc.render.resolution_x=900; sc.render.resolution_y=630
tgt=Vector((0,0.0,1.42))
views={'back':((0,1,0),0.30),'backhigh':((0,1,0.9),0.36),'back34L':((0.8,1,0.35),0.36),'back34R':((-0.8,1,0.35),0.36),'top':((0,0.02,1),0.42)}
want=argv[3].split(',') if len(argv)>3 else list(views)
for k in want:
    d,s=views[k]; d=Vector(d).normalized()
    cam.location=tgt+d*1.0; cd.ortho_scale=s
    cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=prefix+'_'+k+'.png'
    bpy.ops.render.render(write_still=True)
