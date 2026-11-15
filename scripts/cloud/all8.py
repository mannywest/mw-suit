# all 8 standard views in one scene load. args: src prefix [shawlcolour: 'cream'|'' ] [shirt: 'shirt'|''] [views comma list]
import bpy, math, sys
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
src,prefix=argv[0],argv[1]; colour=argv[2] if len(argv)>2 else ''; shirt=len(argv)>3 and argv[3]=='shirt'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc=bpy.context.scene
for o in bpy.data.objects:
    if o.type=='MESH' and o.name!='Jacket':
        o.hide_render = not (shirt and o.name.startswith(('Shirt','Tie')))
J=bpy.data.objects['Jacket']
if colour:
    for m in J.data.materials:
        if m.name in ('Jacket_Lapel_Shawl','Jacket_Lapel_Peak','Jacket_Lapel'):
            nt=m.node_tree; bs=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'][0]
            for l in list(bs.inputs['Base Color'].links): nt.links.remove(l)
            bs.inputs['Base Color'].default_value=(0.80,0.74,0.60,1); bs.inputs['Roughness'].default_value=0.5
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.9,0.9,0.9,1)
L=bpy.data.lights.new("Sun",'SUN'); L.energy=3
lo=bpy.data.objects.new("Sun",L); sc.collection.objects.link(lo)
cd=bpy.data.cameras.new("Cam"); cd.type='ORTHO'
cam=bpy.data.objects.new("Cam",cd); sc.collection.objects.link(cam); sc.camera=cam
sc.view_settings.view_transform='Filmic'; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=16; sc.cycles.use_denoising=False
FR=(math.radians(40),0,math.radians(20)); BK=(math.radians(-50),0,math.radians(160))
# name: (dir, target, scale, res, light)
views={'front':((0,-1,0),(0,0,1.30),0.50,(800,900),FR),'front34':((0.7,-1,0.2),(0,0,1.30),0.50,(800,900),FR),'frontclose':((0,-1,0.15),(0.07,0,1.36),0.22,(800,900),FR),
 'back':((0,1,0),(0,0,1.42),0.30,(900,630),BK),'backhigh':((0,1,0.9),(0,0,1.42),0.36,(900,630),BK),'back34L':((0.8,1,0.35),(0,0,1.42),0.36,(900,630),BK),
 'backclose':((0.5,1,0.35),(-0.04,0,1.44),0.14,(900,630),BK),'backcloseR':((-0.5,1,0.35),(0.04,0,1.44),0.14,(900,630),BK),
 'tipclose':((0,-1,0.1),(0,0,1.15),0.16,(800,900),FR),'tip34':((0.6,-1,0.4),(0,0,1.15),0.2,(800,900),FR),
 'in34':((0.8,-1,0.3),(-0.05,0,1.30),0.25,(800,900),FR),'tipside':((0.9,-1,0.2),(-0.02,0,1.15),0.14,(800,900),FR),
 'side':((1,0,0.0),(0,0.05,1.25),0.45,(800,900),FR),
 'back34R':((-0.8,1,0.35),(0,0,1.42),0.36,(900,630),BK),'top':((0,0.02,1),(0,0,1.42),0.42,(900,630),BK)}
want=argv[4].split(',') if len(argv)>4 else list(views)
for k in want:
    d,t,s,res,rot=views[k]; d=Vector(d).normalized(); t=Vector(t)
    lo.rotation_euler=rot; sc.render.resolution_x,sc.render.resolution_y=res
    cam.location=t+d*1.0; cd.ortho_scale=s; cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=prefix+'_'+k+'.png'; bpy.ops.render.render(write_still=True)
