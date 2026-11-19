#!/usr/bin/env python3
"""Add a real inner LINING layer to a suit GLB.   python3 scripts/add_lining.py IN.glb OUT.glb [--view] [--color=RRGGBB]
For every jacket cloth primitive (Jacket_Wool, Jacket_Lapel*) a copy is added that is flipped inside out and moved 2 mm inward, with its own
material 'Jacket_Lining' (single-sided, plain colour). Anything that used to show the black/ivory inside of the cloth, or the far side of the
jacket seen through a hole, now shows the lining colour in ANY viewer. It does not close holes; it changes what you see through them.
--view  also removes Shirt, Tie and Waistcoat from the scene so the inside of the jacket can be inspected (viewing copy only)."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'check'))
from pygltflib import GLTF2, Accessor, BufferView, Material, PbrMetallicRoughness, Primitive
from seam5 import rd
from seam2 import tris
args = [a for a in sys.argv[1:] if not a.startswith('--')]; src, dst = args[0], args[1]
view = '--view' in sys.argv; col = next((a.split('=')[1] for a in sys.argv if a.startswith('--color=')), '1c2740')
rgb = [int(col[i:i + 2], 16) / 255 for i in (0, 2, 4)]
g = GLTF2().load(src); blob = g.binary_blob(); bl = bytearray(blob)
def addacc(data, typ, ctype, target, mn=None, mx=None):
    while len(bl) % 4: bl.append(0)
    off = len(bl); bl.extend(data.tobytes())
    g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data.tobytes()), target=target))
    g.accessors.append(Accessor(bufferView=len(g.bufferViews) - 1, componentType=ctype, count=len(data), type=typ, min=mn, max=mx))
    return len(g.accessors) - 1
lin = Material(name='Jacket_Lining', pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=rgb + [1], metallicFactor=0.0, roughnessFactor=0.9), doubleSided=False)
g.materials.append(lin); mi = len(g.materials) - 1; added = 0
for mesh in g.meshes:
    cl = [p for p in mesh.primitives if p.material is not None and g.materials[p.material].name.startswith('Jacket_') and g.materials[p.material].name != 'Jacket_Lining']
    if not cl: continue
    a = cl[0].attributes; P = rd(g, blob, a.POSITION, 3); N = rd(g, blob, a.NORMAL, 3)
    Pin = (P - N * 0.002).astype('<f4'); Nin = (-N).astype('<f4')
    ip = addacc(Pin, 'VEC3', 5126, 34962, Pin.min(0).tolist(), Pin.max(0).tolist()); inn = addacc(Nin, 'VEC3', 5126, 34962)
    for p in cl:
        F = tris(g, p.indices); Ff = F[:, [0, 2, 1]].astype('<u4').ravel()
        q = Primitive(attributes=type(p.attributes)(POSITION=ip, NORMAL=inn, TEXCOORD_0=p.attributes.TEXCOORD_0, TEXCOORD_1=p.attributes.TEXCOORD_1), indices=addacc(Ff, 'SCALAR', 5125, 34963), material=mi, mode=4)
        mesh.primitives.append(q); added += len(F)
print('lining triangles added:', added)
if view:
    drop = {'Shirt', 'Tie', 'Waistcoat'}; keep = [n for n in g.scenes[0].nodes if not (g.nodes[n].mesh is not None and g.meshes[g.nodes[n].mesh].name in drop)]
    print('view copy: removed from scene:', [g.nodes[n].name for n in g.scenes[0].nodes if n not in keep]); g.scenes[0].nodes = keep
g.buffers[0].byteLength = len(bl); g.set_binary_blob(bytes(bl)); g.save(dst); print('saved', dst)
