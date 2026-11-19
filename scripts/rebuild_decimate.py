#!/usr/bin/env python3
"""Blender step: load closed shell npz, light smooth, quadric-decimate to target triangles, save npz.  IN.npz OUT.npz [target_tris=90000]"""
import sys, numpy as np, bpy, bmesh
src, out = sys.argv[1], sys.argv[2]; target = int(sys.argv[3]) if len(sys.argv) > 3 else 90000
d = np.load(src); v, f = d['v'].astype(float), d['f'].astype(int)
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('shell'); me.from_pydata(v.tolist(), [], f.tolist()); me.update()
ob = bpy.data.objects.new('shell', me); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
m = ob.modifiers.new('sm', 'SMOOTH'); m.factor = 0.5; m.iterations = 6          # take the voxel stair-steps out
m2 = ob.modifiers.new('dec', 'DECIMATE'); m2.decimate_type = 'COLLAPSE'; m2.ratio = min(1.0, target / len(f))
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); em = ev.to_mesh()
bm = bmesh.new(); bm.from_mesh(em); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.ensure_lookup_table()
V = np.array([x.co[:] for x in bm.verts], 'f4'); Fc = np.array([[x.index for x in fa.verts] for fa in bm.faces], 'u4')
bm.normal_update(); N = np.array([x.normal[:] for x in bm.verts], 'f4')
print('decimated verts', len(V), 'tris', len(Fc)); np.savez_compressed(out, v=V, f=Fc, n=N)
e = np.sort(np.vstack([Fc[:, [0, 1]], Fc[:, [1, 2]], Fc[:, [2, 0]]]), axis=1); _, c = np.unique(e, axis=0, return_counts=True)
print('open edges', int((c == 1).sum()), 'non-manifold', int((c > 2).sum()))
