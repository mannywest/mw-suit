> **Which model file is current? Read MODEL_MAP.md first.** It overrides any 'LATEST' label below (19 Nov 2026).

> **Before saying any model fix works, run `python3 scripts/full_check.py NEW.glb PREVIOUS.glb` (whole jacket, by area) as well as `scripts/check_all.py` (neck only). Report each area as Fixed / Same / Made worse. Add `--sheet out.png` for one combined see-through picture.** (19 Nov 2026: the neck-only check missed pocket, front-edge and shoulder patches.)

# MW Tailleur 3D suit — lapels + collar repair

Role, working method and the full check list: @CLAUDE_ROLE.md (follow it every session).
Latest state, cloud setup and next task (shawl lapel): @HANDOFF_2026-11-15.md (read it first). Base-jacket + swappable-lapel plan: @LAPEL_BASE_PLAN.md.
Manny's rule from 15 Nov: fix every issue you have noticed before reporting; never report an incomplete step as finished.

Owner: Manny (MW Tailleur). He is not a coder: explain simply, keep replies short, and never call a result "done" until he confirms from his own screenshot or a render you have actually looked at.
Keep token use low: check with numbers first, render only to confirm, look at few images. Do ONE repair step per session, then stop and show Manny.

## Rules
- Never modify MW_Tailleur_suit_repaired_v2.glb (original) or earlier versions. Save each result as a NEW file.
- Manny has approved changing the notch lapel (Jacket_Lapel) and the peak lapel (Jacket_Lapel_Peak) for this repair. You choose which side to mirror.
- Keep TEXCOORD_1 and all other parts (waistcoat, trousers, shirt, tie, buttons) unchanged.
- Do not call the result photorealistic. No DoubleSide hacks, no global remesh.
- Validate every GLB you export: zero errors. `cd tools && npm install` once (installs gltf-validator 2.0.0-dev.3.10), then `node tools/validate.js /full/path/file.glb`.
- Put test files in the scratchpad. Only final results and renders for Manny go in this folder; never overwrite Manny's existing PNGs.

## Tools on this Mac (2015 MacBook Air, macOS 12, 8 GB)
- Blender 3.6.23: /Applications/Blender.app/Contents/MacOS/Blender (slow; render in background with Cycles CPU, low samples). Cannot read meshopt GLBs: use *_blender*.glb.
- Python with pygltflib/numpy/pillow: `~/Library/Python/3.12/bin/uv run --with pygltflib --with numpy --with pillow python ...`
- Never name a script after a Python module (e.g. inspect.py) — it breaks numpy.
- scripts/check/ (pass that folder as the first argument):
  - common.py: load(glb) -> g, blob, P, N, U0, U1, Fs (Fs = triangle lists for jacket primitives: 0 body Jacket_Wool, 1 notch Jacket_Lapel, 2 peak Jacket_Lapel_Peak, 3 Trousers_Wool). depthmap() = orthographic back-view z-buffer.
  - gaps.py / gapview.py: count see-through holes (straight back / any view direction).
  - sym.py: left/right mirror mismatch of the lapels (mm).
  - render_views.py: Blender back/backhigh/back34L/back34R/top renders; third argument = a material to hide (shows one lapel style only).
  - front_views.py: Blender front/front34/frontclose renders, same hide option.
  - an.py: colour-coded flat render (body grey, collar red/blue) to see which part is which.

## Model facts (glTF axes: y up, z>0 = front, z<0 = back, x = left/right)
- The Jacket mesh holds BOTH lapel styles in the same place. The app (mw_app_code.zip, src/main.ts) shows only one at a time. In Blender both show together and look like "two layers"; in Cycles the overlap can show black triangles. Always judge each style on its own.
- All jacket primitives share one vertex buffer. Rebuilt peak vertices are index >= 34307.
- The back panel has duplicate vertices along panel seams and some real tears (missing triangles).

## Files
- MW_Tailleur_suit_repaired_v2.glb: original, do not edit.
- MW_Tailleur_suit_v4_blender_collarfix2.glb: state before the rear collar seam work.
- MW_Tailleur_suit_v4_blender_collarfix3.glb: older seam attempt (ragged).
- MW_Tailleur_suit_v4_blender_collarfix4.glb: LATEST. Made by scripts/seam6.py from collarfix2. Validated: 0 errors.
  Rear seam = one smooth curve (level at y 1.440 m, curving into the shoulder line at |x| 0.125), cut with overlap so no gaps, 3 missing back-panel triangles filled, 4 peak spike triangles at the side of the neck removed.
  Manny saw only "slight improvement" in Blender (he was seeing both lapels at once).
- MW_Tailleur_suit_v4_blender_collarfix4_notch_only.glb / _peak_only.glb: repair step 1 (scripts/split_styles.py removes the other style's primitive; all vertex data unchanged). Validated: 0 errors. Render: render_step1_notch_vs_peak_front.png.
- MW_Tailleur_suit_v4_blender_collarfix4_peak_step2.glb: repair step 2 (scripts/peak_step2.py, input = _peak_only). Peak lapel rebuilt: same outline, inner edge follows the jacket front edge (strip gone), surface shape taken from the smooth notch lapel, no panels inside the neck, edge walls down to the jacket. Peak collar pieces and everything else unchanged. Validated: 0 errors. Renders: render_step2_peak_front.png / _back.png. NOT complete (review 15 Nov): dark shards where collar meets peak top, pale strip along peak top edge (edge wall), peak tips stand up as flat 'ears' over the shoulders in backhigh view (edge walls up to 40 mm), dark holes beside the neck. Next: fix these in step 2 before step 3.
- MW_Tailleur_suit_v4_blender_collarfix4_peak_step2b.glb: step 2 continued (scripts/peak_step2b.py, input = _peak_only). Validated: 0 errors. Renders: render_step2b_peak_*.png (all 8 views).
  Lapel top = straight gorge line G(0.063,1.445)->V(0.122,1.394), peak tip lowered to (0.150,1.410); upper lapel lies ~4 mm on the chest (blended from y 1.29 up; lower lapel unchanged); old ragged front collar ends cut (collar tris with max z >= -0.035) and rebuilt as one band per side whose lower edge = lapel gorge points; collar point 2 mm off the peak edge; 106 tiny body slivers near (|x| .11-.14, y 1.41) removed.
  Front views clean (no shards, no pale strip, tight V, tips flat). NOT complete: visible step/ragged join where the new band meets the old collar at the sides of the neck (back, back34L/R, top), small dark hole at that join in back34R; gorge seam not visible as a line (collar and lapel shade as one surface). Hole pixels (gapview, 6 dirs) 798 vs 2575 before, but 4 directions worse, all at that join (|x| .07-.085, y 1.46-1.48). Next: clip the old collar cleanly at the cut and stitch the band to it.
- Mac disk is nearly full (often < 50 MB free; each GLB ~20 MB). Run `df -m /System/Volumes/Data` before saving; delete scratch GLBs after use.
- Shawl lapel idea (14 Nov 2026): Manny asked about it; suggested a freelancer build it, or Claude tries it as a test after step 4.
- Renders: render_back_collar_*.png = before; render_collarfix4_*.png = after.

## Findings (14 Nov 2026)
- Peak lapel alone: a thin extra strip runs down the inside edge of both lapels from collar to button, plus dark gaps under both peak tips. The "two tall flat panels inside the neck" (from above) are peak-lapel material, probably the same strip.
- Symmetry (sym.py, front part z>0): peak median 1.3 mm / 90% 3 mm / max 28 mm; notch median 3.9 mm / 90% 10.6 mm / max 33 mm, worst near the gorge/notch (y 1.36–1.44); notch left lapel runs ~3 cm lower than right. Below the top button some asymmetry is natural (left front wraps over right); above it the lapels should match.
- Notch collar points stick out like wings over the shoulders when seen from above-behind (at x ±0.143, y 1.39, z +0.07).
- Collar edges are jagged at the sides of the neck (where the collar turns to the front) and along the top edge; the shoulder corners have shards and flaps.

## Peak lapel reference (Manny's photo, 15 Nov 2026: one-button dinner jacket, satin peak lapels)
- Collar point and top of the peak meet in a very tight V: almost touching, no open hole (our model: ~1 cm gap).
- Gorge seam: one clean line, set high near the collarbone, from collar into the base of the peak; nothing sticks out.
- Peak: sharp, points up and out toward the shoulder, lies flat on the chest, stays below the shoulder line.
- Collar: narrow at the front, sits close to the neck, flows straight into the gorge; roll line continuous from button into collar.
- Lapel outer edge: smooth curve with slight belly. Edge stitching is texture only.
- Keep our lapel width/length/button point (Manny confirmed 15 Nov: fix ONLY the collar join and the peak tips).
- Photo saved as reference_peak_lapel.png (Manny's file; never overwrite).
- Next session (still step 2): rebuild the front collar ends of the peak collar so they share one gorge line with the peak top (tight V, no gap, no shards); bring the peak tips down below the shoulder line; edge walls a few mm only (no pale strip); close the holes beside the neck. Input: MW_Tailleur_suit_v4_blender_collarfix4_peak_step2.glb (or rerun scripts/peak_step2.py). Run the full check list in CLAUDE_ROLE.md.

## Repair plan (Manny approved; one step per session, show renders, wait for his OK)
1. Separate files: notch-only and peak-only GLBs from collarfix4 (delete the other style's triangles), so each style can be reviewed alone in Blender.
2. Peak lapel: remove the extra inner strip and the panels inside the neck; close the gaps under the peak tips; then smooth the peak lapel surface (it looks lumpy/creased next to the smooth notch lapel; Manny wants it to match the notch finish).
3. Notch lapel: mirror the better side onto the other side above the top button; keep the natural overlap below it; fix the wing points.
4. Collar: smooth the jagged side and top edges, remove shards and flaps at the shoulder corners.
If patching cannot reach Manny's standard, write a brief for a 3D garment freelancer (Marvelous Designer / CLO3D rebuild).
Manny checks in Blender: File > Import > glTF 2.0, select Jacket, View > Viewpoint > Back (or Front), Shift+B to box-zoom.
