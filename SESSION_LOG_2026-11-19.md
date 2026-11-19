# Session log - 2026-11-19 (base jacket side repair, new checks)

## Honest status in one paragraph
Pocket-side see-through area on the lapel-free base was cut from 17,417 to about 3,500 mm2 and the side strip was rebuilt as smooth panels,
but the result is NOT clean: new open edges and loose pieces were added, the right-side hem still shows ragged slivers, and the front chest /
lapel area, shoulders and neck gap are untouched. Nothing here is on the website yet (the website models notch/peak/shawl.glb are built from
older files and do not contain any of these repairs).

## Files (all repo root, lapel-free base). Latest candidate = F3. See MODEL_MAP.md.
| file | what it is | made by |
|---|---|---|
| BASE_stepD_shardfree | previous base (reference) | - |
| BASE_stepE_sides | stepD + ~5,200 tris of new cloth over pocket-side/hem/back holes | scripts/base_e_sides.py |
| BASE_stepF3_trimmed | stepE with the side strips rebuilt as smooth panels (scripts/base_f_panels.py), junction gaps closed (base_f2_close.py), loose right-hem flaps removed + refilled (base_f3_trim.py) | see scripts |
Intermediate files (E2 smoothed, F panels, F2 closed) are not kept: they are reproducible with the scripts and were superseded.
base_e_smooth.py and base_g_frontedge.py are EXPERIMENTS that traded one problem for another (more inside-out triangles); no model from them is kept.

## Measured (full_check.py; lower is better)
| area | stepD | stepE | stepF3 |
|---|---|---|---|
| see-through pocket sides mm2 | 17,417 | 3,497 | ~3,600 |
| see-through hem mm2 | 628 | 120 | 312 |
| see-through sleeve mm2 | 0 | 9 | 12 |
| see-through front chest mm2 | 12,616 | 12,633 | ~12,600 (untouched) |
| bumps total (new check) | 357 | 447 | ~480 |
Made worse by the repairs: open edges, loose pieces, some sharp folds; weave stretch on new cloth slightly above the original.

## New tools
- scripts/bumps.py (also run inside full_check.py): lumps/dents, with locations. Added because the old checks could not see crumpled surfaces.
- full_check.py: fixed a crash when a see-through patch's centre pixel was empty.
- configurator: lining option "Match jacket (default)" (inside faces keep the jacket colour).

## Why the checks missed the user's screenshots
They measured holes and edge lengths only. They had no test for lumps/pits, listed only the 8 biggest patches, and said lumpiness
"needs your eyes". Bump check now exists; hem edge jaggedness and the light strip near the cuff are still not measured.

## Finding about the "black void" at the front chest
Much of the front-chest see-through is the inside of the opposite front panel seen through the lapel-free opening. In viewers that do not
draw a lining it shows black. Options: (a) a real lining layer in the GLB (inside surface, own material) - not built; (b) leave it to the
website lining shader. With a lapel attached the void shrinks but does not disappear (notch ~3.1k, shawl ~7.5k, peak ~8.2k mm2 front chest).

## Open items (not done)
1. Front chest / lapel area: base edge trimmed cleanly + each lapel tested on it (front-edge smoothing tried, discarded).
2. Right-side hem slivers; light strip near the cuff (cause unknown).
3. Shoulder patches (~6.8k mm2), back patches (~1.8k), neck gap on notch, crumpled fold on peak lapel.
4. Apply the verified repairs to the website models (they carry their own body copy).
5. Real Den Vi fabric tiles; Milanese buttonhole styles 01/02/08.
