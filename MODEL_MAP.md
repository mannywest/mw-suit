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
- MW_Tailleur_suit_v4_BASE_stepE_sides.glb  = stepD + new cloth over pocket-side holes (CANDIDATE)
- MW_Tailleur_suit_v4_BASE_stepF3_trimmed.glb = latest side-panel rebuild (CANDIDATE, still has hem slivers; lapel area untouched)
- Full results and caveats: SESSION_LOG_2026-11-19.md. stepD remains the last file that was fully reviewed.
