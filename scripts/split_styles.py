# Repair step 1: make notch-only and peak-only copies of collarfix4.
# Only change: the other lapel style's primitive is removed from the Jacket mesh.
import sys
from pygltflib import GLTF2

SRC = '/Users/mannywest/Projects/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4.glb'
OUT = {'Jacket_Lapel_Peak': '/Users/mannywest/Projects/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_notch_only.glb',
       'Jacket_Lapel':      '/Users/mannywest/Projects/mw-suit/MW_Tailleur_suit_v4_blender_collarfix4_peak_only.glb'}

for drop, out in OUT.items():
    g = GLTF2().load(SRC)
    jacket = next(m for m in g.meshes if m.name == 'Jacket')
    before = len(jacket.primitives)
    jacket.primitives = [p for p in jacket.primitives
                         if p.material is None or g.materials[p.material].name != drop]
    assert len(jacket.primitives) == before - 1, drop
    g.save(out)
    print('removed', drop, '->', out)
