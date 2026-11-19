# MW Tailleur suit models: which file is which (19 Nov 2026)

Status words: LIVE = shipped on the website. BASE = lapel-free jacket, the future foundation.
LATEST = newest of its kind. OLD = earlier step, safe to ignore. UNSURE = I could not confirm.

Checked with `python3 scripts/check_all.py` (NECK only: holes from 6 angles, shirt poke-through, validator) and `python3 scripts/full_check.py` (WHOLE jacket by area: see-through patches, open edges, shards, spikes, creases, symmetry, UV).
A low count is necessary, not sufficient. Close-up renders have not been compared yet.

## 1. What the website uses now (configurator/public/models, matched by triangle counts)

| Website file | Built from | Neck holes | Shirt poke | Note |
|---|---|---|---|---|
| notch.glb | MW_Tailleur_suit_v4_blender_collarfix4_notch_only.glb | 1067 | 424 mm2 | Whole-jacket route. High-angle neck gap. Worst of the three. |
| peak.glb  | MW_Tailleur_suit_v4_blender_collarfix4_peak_step2d_shoulders.glb | 27 | 0 | Whole-jacket route. Best of the three. |
| shawl.glb | MW_Tailleur_suit_v4_SHAWL_step1.glb | 62 | 1.5 mm2 | Modified copy of the base body plus shawl lapel. |

None of the three website models uses the BASE files.

## 2. Lapel-free base (the plan in LAPEL_BASE_PLAN.md)

| File | Status | Neck holes | Shirt poke |
|---|---|---|---|
| MW_Tailleur_suit_v4_BASE_stepD_shardfree.glb | BASE, LATEST (jacket body only differs from stepC: 259 fewer triangles, probably stray shards removed; not confirmed) | 142 | 276 mm2 |
| MW_Tailleur_suit_v4_BASE_stepC_neck.glb | OLD (stepD supersedes it) | 142 | 276 mm2 |
| MW_Tailleur_suit_v4_BASE_stepB_cleanrim.glb | OLD | not run | not run |
| MW_Tailleur_suit_v4_BASE_stepA_neckrim.glb | OLD | 857 | 132 mm2 |

Base is not finished: open flaws are in HANDOFF_2026-11-15.md (neck side gaps, back-centre slit, notches, shoulder corners, lapel seam points).

## 3. Whole-jacket files (lapel built in)

| File | Status |
|---|---|
| ..._collarfix4_notch_only.glb | LIVE notch |
| ..._collarfix4_peak_step2d_shoulders.glb | LIVE peak, LATEST peak |
| MW_Tailleur_suit_v4_SHAWL_step1.glb | LIVE shawl, LATEST shawl |
| ..._collarfix4_peak_step2b.glb | OLD (1165 holes) |
| ..._collarfix4_peak_step2.glb, _peak_step2c_onepiece.glb, _peak_step2c_onepiece_v2.glb, _peak_only.glb | OLD, UNSURE (steps between or beside 2b and 2d; not checked) |
| ..._collarfix4.glb, ..._collarfix2.glb | OLD, UNSURE (earlier collar repairs) |
| MW_Tailleur_suit_repaired_v2.glb | OLD, UNSURE (earliest repair) |

## 4. Where things are going

Build one clean base, then plug notch, peak and shawl onto it. Today only the base exists (unfinished) and the shawl is a partial start.


## Added 2026-11-19 (candidates, NOT on the website)
- MW_Tailleur_suit_v4_BASE_stepE_sides.glb  = stepD + new cloth over pocket-side holes (REJECTED 2026-11-19: less see-through but more edges/bumps/slivers; original looked better)
- MW_Tailleur_suit_v4_BASE_stepF3_trimmed.glb = side-panel rebuild (REJECTED 2026-11-19: ragged hem, slivers, more errors than stepD)
- Full results and caveats: SESSION_LOG_2026-11-19.md. **stepD remains the base to use** (owner decision 2026-11-19: the originals looked better and had fewer errors).
- MW_Tailleur_suit_v4_SHAWL_step2_frontcut.glb / ..._peak_step3_frontcut.glb = front-edge cut experiments (NOT adopted; shawl tip spike remains; the cut made the notch worse so none was made for notch)

## Lining layer (2026-11-19)
- scripts/add_lining.py adds a real inner lining layer (own material Jacket_Lining, default navy) to any suit GLB. It does NOT close holes; it makes what shows through them the lining colour in any viewer.
- BASE_stepD_lined = stepD + lining. BASE_stepD_lined_VIEWCOPY_no_shirt_waistcoat = same, with shirt, tie and waistcoat removed to inspect the inside (viewing copy only; the configurator cannot load it).
- Configurator/website do not use the lining layer yet (their shader still colours inside faces).

## Rebuild attempt 1 (2026-11-19) - EXPERIMENT, not adopted
- scripts/rebuild_body.py (voxel closing -> closed 3 mm shell), rebuild_decimate.py (Blender bpy: smooth + decimate to 90k), rebuild_finish.py (wool/lining split, UVs from nearest old triangle, weld).
- MW_Tailleur_suit_v5_REBUILD_try1(.glb / _no_shirt_waistcoat.glb): big pocket/side/back/hem holes and back seam cracks gone; shell is fully closed. BUT bumpy (261 bumps, max 7.2 mm), UV stretch outliers 7,755 (old ~1,200), lining flecks on outer face, pocket/front-edge detail softened, lapels not rebuilt. stepD stays the base.

## Rebuild (2026-11-19) - body + lapels, EXPERIMENT awaiting user review (website still uses the original models)
- Files: MW_Tailleur_suit_v5_REBUILD_BASE / _notch / _peak / _shawl .glb (replace try1-3, deleted).
- Recipe (all in scripts/): rebuild_suit.sh IN OUT LAPEL_MAT -> rebuild_body.sh (voxel closing R=6 mm + local wider closings at the old holes, smoothed field, Blender smooth+decimate 90k, wool/lining split by normals+ray+growing, cloth kept near old edges, world-space 30 mm fabric UV1, shell pulled in 0.9 mm) then rebuild_lapel.sh (same idea at 1.5 mm voxels, 14k tris, underside = cloth).
- Wins: big pocket/side/back/hem/shoulder holes and back seam cracks gone; bumps ~360 -> 1-4; slivers ~750 -> 60-70; fabric UV stretch down; shawl tip spike gone; see-through totals roughly halved or better.
- Worse/unfinished: creases in front chest (thin-shell edges of the rebuilt lapel), nonmanifold/spikes up on peak and shawl (lapel/body junction), notch step less crisp, small specks on chest, ragged lining-colour sliver along front edge, two shoulder-top checker patches (render looks solid), neck gap on notch remains.
